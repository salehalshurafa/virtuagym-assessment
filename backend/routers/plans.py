import logging
from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from db import get_session
from models import (
    Plan,
    PlanDay,
    PlanTemplate,
    User,
    UserPlanAssignment,
    UserPlanAssignmentStatus,
    WeeklyWorkoutPlan,
)
from routers.deps import get_current_user
from schemas import (
    BulkAssignConflict,
    BulkAssignResponse,
    BulkAssignResult,
    PlanCreate,
    PlanDayCreate,
    PlanFromTemplateRequest,
    PlanRead,
    PlanUpdate,
    serialize_plan,
)
from services import assignment_service
from services.mailer import Mailer, get_mailer
from services.plan_diff import compute_plan_diff, snapshot_plan
from services.plan_service import (
    attach_weeks_to_plan,
    materialize_plan,
    materialize_plan_day,
    total_days,
)
from services.template_service import instantiate_plan_template


def actor_name(actor: User) -> str:
    name = f"{actor.first_name} {actor.last_name}".strip()
    return name or actor.email

logger = logging.getLogger("virtuagym.plans")

router = APIRouter(tags=["plans"])


def get_or_404(session: Session, plan_id: str, *, allow_archived: bool = True) -> Plan:
    plan = session.get(Plan, plan_id)

    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if plan.archived and not allow_archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan is archived")
    
    return plan


def active_assignee_emails(plan: Plan) -> list[str]:
    emails: list[str] = []

    for a in plan.assignments:
        if a.status in (UserPlanAssignmentStatus.in_progress, UserPlanAssignmentStatus.paused):
            if a.user is not None and a.user.email:
                emails.append(a.user.email)

    return emails


@router.get("/active", response_model_exclude_none=True)
def list_active_plans(session: Session = Depends(get_session)) -> list[dict]:
    rows = session.exec(
        select(Plan).where(Plan.archived == False).order_by(Plan.title)
    ).all()

    out: list[dict] = []
    for plan in rows:
        active = [
            a
            for a in plan.assignments
            if a.status
            in (UserPlanAssignmentStatus.in_progress, UserPlanAssignmentStatus.paused)
            and a.user is not None
            and not a.user.removed
        ]
        if not active:
            continue

        statuses = {a.status.value for a in active}
        if len(statuses) == 1:
            status_summary = next(iter(statuses))
        else:
            status_summary = "mixed"

        most_recent_start = max((a.start_date for a in active), default=None)

        plan_payload = serialize_plan(plan).model_dump(by_alias=True, exclude_none=True)
        plan_payload["assignees"] = [
            {
                "id": a.user.id,
                "firstName": a.user.first_name,
                "lastName": a.user.last_name,
            }
            for a in active
        ]
        plan_payload["statusSummary"] = status_summary
        plan_payload["_sortKey"] = most_recent_start.isoformat() if most_recent_start else ""
        out.append(plan_payload)

    out.sort(key=lambda r: r.pop("_sortKey", ""), reverse=True)
    return out


@router.get("", response_model=List[PlanRead], response_model_exclude_none=True)
def list_plans(
    include_archived: bool = False,
    session: Session = Depends(get_session),
) -> List[PlanRead]:
    statement = select(Plan)
    if not include_archived:
        statement = statement.where(Plan.archived == False)
    statement = statement.order_by(Plan.title)

    rows = session.exec(statement).all()

    return [serialize_plan(p) for p in rows]


@router.get("/{plan_id}", response_model=PlanRead, response_model_exclude_none=True)
def get_plan(plan_id: str, session: Session = Depends(get_session)) -> PlanRead:
    return serialize_plan(get_or_404(session, plan_id))


@router.post("", response_model=PlanRead, response_model_exclude_none=True, status_code=201)
def create_plan(payload: PlanCreate, session: Session = Depends(get_session)) -> PlanRead:
    try:
        plan = materialize_plan(session, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    session.add(plan)
    session.commit()
    session.refresh(plan)

    return serialize_plan(plan)


@router.post(
    "/from-template",
    response_model=BulkAssignResponse,
    response_model_exclude_none=True,
    status_code=201,
)
async def create_plan_from_template(
    payload: PlanFromTemplateRequest,
    session: Session = Depends(get_session),
    mailer: Mailer = Depends(get_mailer),
    current_user: User = Depends(get_current_user),
) -> BulkAssignResponse:
    template = session.get(PlanTemplate, payload.template_id)
    if template is None or template.archived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan template not found"
        )

    try:
        plan = instantiate_plan_template(session, template)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    session.add(plan)
    session.flush()

    duration_days = total_days(plan.duration, plan.duration_type)
    force = set(payload.force_replace_user_ids)
    results: List[BulkAssignResult] = []
    notify_emails: list[str] = []

    for user_id in payload.user_ids:
        user = session.get(User, user_id)
        if user is None or user.removed:
            results.append(
                BulkAssignResult(user_id=user_id, success=False, reason="USER_NOT_FOUND")
            )
            continue

        existing = session.exec(
            select(UserPlanAssignment).where(
                UserPlanAssignment.user_id == user.id,
                UserPlanAssignment.status.in_(
                    [
                        UserPlanAssignmentStatus.in_progress,
                        UserPlanAssignmentStatus.paused,
                    ]
                ),
            )
        ).first()

        if existing is not None and user_id not in force:
            results.append(
                BulkAssignResult(
                    user_id=user_id,
                    success=False,
                    reason="CONFLICT_ACTIVE_PLAN",
                    conflict_with=BulkAssignConflict(
                        plan_title=existing.plan.title if existing.plan else "(unknown)",
                    ),
                )
            )
            continue

        try:
            with session.begin_nested():
                if existing is not None:
                    assignment_service.cancel(existing)
                    session.add(existing)
                    session.flush()

                new_assignment = UserPlanAssignment(
                    user_id=user.id,
                    plan_id=plan.id,
                    start_date=payload.start_date,
                    end_date=payload.start_date + timedelta(days=duration_days),
                    status=UserPlanAssignmentStatus.in_progress,
                    assigned_by_name=actor_name(current_user),
                    assigned_by_email=current_user.email,
                )
                session.add(new_assignment)
                session.flush()
                created_id = new_assignment.id
        except SQLAlchemyError as e:
            logger.warning(
                "create_plan_from_template: per-user DB failure for user_id=%s: %s",
                user_id,
                e,
            )
            results.append(
                BulkAssignResult(user_id=user_id, success=False, reason="DB_ERROR")
            )
            continue

        results.append(
            BulkAssignResult(user_id=user_id, success=True, assignment_id=created_id)
        )
        notify_emails.append(user.email)

    session.commit()

    for email in notify_emails:
        try:
            await mailer.send_plan_assigned(email, plan, actor=current_user)
        except Exception:
            pass

    return BulkAssignResponse(plan_id=plan.id, results=results)


@router.patch("/{plan_id}", response_model=PlanRead, response_model_exclude_none=True)
async def update_plan(
    plan_id: str,
    payload: PlanUpdate,
    session: Session = Depends(get_session),
    mailer: Mailer = Depends(get_mailer),
    current_user: User = Depends(get_current_user),
) -> PlanRead:
    plan = get_or_404(session, plan_id, allow_archived=False)
    pre_snapshot = snapshot_plan(plan)

    updates = payload.model_dump(exclude_unset=True)

    weekly_plans_replacement = updates.pop("weekly_plans", None)
    flat_days_replacement = updates.pop("flat_days", None)

    old_total_days = total_days(plan.duration, plan.duration_type)

    for field, value in updates.items():
        setattr(plan, field, value)

    if weekly_plans_replacement is not None:
        from schemas import WeeklyWorkoutPlanCreate

        for wp in list(plan.weekly_plans):
            session.delete(wp)
        plan.weekly_plans = []
        try:
            attach_weeks_to_plan(
                session,
                plan,
                [WeeklyWorkoutPlanCreate(**w) for w in weekly_plans_replacement],
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if flat_days_replacement is not None:
        for d in list(plan.flat_days):
            session.delete(d)
        plan.flat_days = []
        for day_payload in flat_days_replacement:
            plan.flat_days.append(materialize_plan_day(PlanDayCreate(**day_payload), session))

    new_total_days = total_days(plan.duration, plan.duration_type)
    if new_total_days != old_total_days:
        for a in plan.assignments:
            if a.status in (
                UserPlanAssignmentStatus.in_progress,
                UserPlanAssignmentStatus.paused,
            ):
                a.end_date = a.start_date + timedelta(days=new_total_days)
                if a.status == UserPlanAssignmentStatus.paused:
                    a.remaining_days = None
                session.add(a)

    session.add(plan)
    session.commit()
    session.refresh(plan)

    recipients = active_assignee_emails(plan)
    if recipients:
        post_snapshot = snapshot_plan(plan)
        changes = compute_plan_diff(pre_snapshot, post_snapshot)
        for email in recipients:
            try:
                await mailer.send_plan_modified(
                    email, plan, actor=current_user, changes=changes
                )
            except Exception:
                pass 

    return serialize_plan(plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_plan(
    plan_id: str,
    session: Session = Depends(get_session),
    mailer: Mailer = Depends(get_mailer),
    current_user: User = Depends(get_current_user),
) -> None:
    plan = get_or_404(session, plan_id)
    if plan.archived:
        return 

    recipients = active_assignee_emails(plan)
    plan_title = plan.title

    plan.archived = True
    session.add(plan)
    session.commit()

    for email in recipients:
        try:
            await mailer.send_plan_archived(email, plan_title, actor=current_user)
        except Exception:
            pass