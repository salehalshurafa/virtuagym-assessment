import logging
from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from db import get_session
from models import (
    Plan,
    User,
    UserPlanAssignment,
    UserPlanAssignmentStatus,
)
from routers.deps import get_current_user
from schemas import (
    BulkAssignConflict,
    BulkAssignRequest,
    BulkAssignResponse,
    BulkAssignResult,
    RepointMultiRequest,
    RepointMultiResponse,
    RepointResult,
    UserPlanAssignmentCreate,
    UserPlanAssignmentRead,
    UserPlanAssignmentUpdate,
    serialize_assignment,
)
from schemas.schedule import ScheduleEntry
from services import assignment_service
from services.clock import today_for
from services.mailer import Mailer, get_mailer
from services.plan_diff import compute_plan_diff, snapshot_plan
from services.plan_service import total_days
from services.schedule_service import compute_schedule


def derive_full_name(user: User) -> str:
    name = f"{user.first_name} {user.last_name}".strip()
    return name or user.email

logger = logging.getLogger("virtuagym.assignments")

router = APIRouter(tags=["assignments"])


def get_or_404(session: Session, assignment_id: str) -> UserPlanAssignment:
    a = session.get(UserPlanAssignment, assignment_id)
    if a is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
        )
    return a

@router.get(
    "",
    response_model=List[UserPlanAssignmentRead],
    response_model_exclude_none=True,
)
def list_assignments(
    user_id: Optional[str] = None,
    plan_id: Optional[str] = None,
    status_filter: Optional[UserPlanAssignmentStatus] = None,
    session: Session = Depends(get_session),
) -> List[UserPlanAssignmentRead]:
    statement = select(UserPlanAssignment)
    if user_id is not None:
        statement = statement.where(UserPlanAssignment.user_id == user_id)
    if plan_id is not None:
        statement = statement.where(UserPlanAssignment.plan_id == plan_id)
    if status_filter is not None:
        statement = statement.where(UserPlanAssignment.status == status_filter)
    statement = statement.order_by(UserPlanAssignment.start_date.desc())
    return [serialize_assignment(a) for a in session.exec(statement).all()]


@router.get(
    "/{assignment_id}",
    response_model=UserPlanAssignmentRead,
    response_model_exclude_none=True,
)
def get_assignment(
    assignment_id: str, session: Session = Depends(get_session)
) -> UserPlanAssignmentRead:
    return serialize_assignment(get_or_404(session, assignment_id))

@router.post(
    "",
    response_model=UserPlanAssignmentRead,
    response_model_exclude_none=True,
    status_code=201,
)
async def create_assignment(
    payload: UserPlanAssignmentCreate,
    session: Session = Depends(get_session),
    mailer: Mailer = Depends(get_mailer),
    current_user: User = Depends(get_current_user),
) -> UserPlanAssignmentRead:
    user = session.get(User, payload.user_id)
    if user is None or user.removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    plan = session.get(Plan, payload.plan_id)
    if plan is None or plan.archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    statement = select(UserPlanAssignment).where(
            UserPlanAssignment.user_id == user.id,
            UserPlanAssignment.status == UserPlanAssignmentStatus.in_progress,
        )
    existing_active = session.exec(statement).first()

    if existing_active is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "User already has an in-progress assignment. "
                "Cancel or complete it before assigning a new plan."
            ),
        )

    duration_days = total_days(plan.duration, plan.duration_type)
    assignment = UserPlanAssignment(
        user_id=user.id,
        plan_id=plan.id,
        start_date=payload.start_date,
        end_date=payload.start_date + timedelta(days=duration_days),
        status=UserPlanAssignmentStatus.in_progress,
        assigned_by_name=derive_full_name(current_user),
        assigned_by_email=current_user.email,
    )
    session.add(assignment)
    session.commit()
    session.refresh(assignment)

    try:
        await mailer.send_plan_assigned(user.email, plan, actor=current_user)
    except Exception:
        pass

    return serialize_assignment(assignment)

@router.patch(
    "/{assignment_id}",
    response_model=UserPlanAssignmentRead,
    response_model_exclude_none=True,
)
def update_assignment(
    assignment_id: str,
    payload: UserPlanAssignmentUpdate,
    session: Session = Depends(get_session),
) -> UserPlanAssignmentRead:
    a = get_or_404(session, assignment_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(a, field, value)
    session.add(a)
    session.commit()
    session.refresh(a)
    return serialize_assignment(a)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: str, session: Session = Depends(get_session)
) -> None:
    a = get_or_404(session, assignment_id)
    session.delete(a)
    session.commit()


@router.post(
    "/bulk",
    response_model=BulkAssignResponse,
    response_model_exclude_none=True,
)
async def bulk_assign(
    payload: BulkAssignRequest,
    session: Session = Depends(get_session),
    mailer: Mailer = Depends(get_mailer),
    current_user: User = Depends(get_current_user),
) -> BulkAssignResponse:
    plan = session.get(Plan, payload.plan_id)
    if plan is None or plan.archived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )

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

        # Per-user SAVEPOINT — a flush failure for this user (e.g. a partial
        # unique index race) rolls back only this user's changes, leaving
        # earlier successful users in the outer transaction.
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
                    assigned_by_name=derive_full_name(current_user),
                    assigned_by_email=current_user.email,
                )
                session.add(new_assignment)
                session.flush()
                created_id = new_assignment.id
        except SQLAlchemyError as e:
            logger.warning(
                "bulk_assign: per-user DB failure for user_id=%s: %s", user_id, e
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

@router.post(
    "/repoint-multi",
    response_model=RepointMultiResponse,
    response_model_exclude_none=True,
)
async def repoint_multi(
    payload: RepointMultiRequest,
    session: Session = Depends(get_session),
    mailer: Mailer = Depends(get_mailer),
    current_user: User = Depends(get_current_user),
) -> RepointMultiResponse:
    new_plan = session.get(Plan, payload.plan_id)
    if new_plan is None or new_plan.archived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Target plan not found"
        )

    new_total = total_days(new_plan.duration, new_plan.duration_type)
    new_snapshot = snapshot_plan(new_plan)
    results: List[RepointResult] = []
    
    notify: list[tuple[str, dict]] = []

    for aid in payload.assignment_ids:
        a = session.get(UserPlanAssignment, aid)
        if a is None:
            results.append(
                RepointResult(assignment_id=aid, success=False, error="NOT_FOUND")
            )
            continue
        old_snapshot = snapshot_plan(a.plan) if a.plan is not None else None
        a.plan_id = new_plan.id
        a.end_date = a.start_date + timedelta(days=new_total)

        if a.status == UserPlanAssignmentStatus.paused:
            a.remaining_days = None
        session.add(a)
        results.append(RepointResult(assignment_id=aid, success=True))
        if a.user is not None and a.user.email and old_snapshot is not None:
            notify.append((a.user.email, old_snapshot))

    session.commit()

    for email, old_snapshot in notify:
        try:
            changes = compute_plan_diff(old_snapshot, new_snapshot)
            await mailer.send_plan_modified(
                email, new_plan, actor=current_user, changes=changes
            )
        except Exception:
            pass

    return RepointMultiResponse(plan_id=new_plan.id, results=results)


@router.post(
    "/{assignment_id}/pause",
    response_model=UserPlanAssignmentRead,
    response_model_exclude_none=True,
)
async def pause_assignment(
    assignment_id: str,
    session: Session = Depends(get_session),
    mailer: Mailer = Depends(get_mailer),
    current_user: User = Depends(get_current_user),
) -> UserPlanAssignmentRead:
    a = get_or_404(session, assignment_id)
    
    assignment_service.pause(a, today=today_for(a.user))
    session.add(a)
    session.commit()
    session.refresh(a)

    if a.user is not None and a.plan is not None and a.user.email:
        try:
            await mailer.send_plan_paused(a.user.email, a.plan, actor=current_user)
        except Exception:
            pass

    return serialize_assignment(a)


@router.post(
    "/{assignment_id}/resume",
    response_model=UserPlanAssignmentRead,
    response_model_exclude_none=True,
)
async def resume_assignment(
    assignment_id: str,
    session: Session = Depends(get_session),
    mailer: Mailer = Depends(get_mailer),
    current_user: User = Depends(get_current_user),
) -> UserPlanAssignmentRead:
    a = get_or_404(session, assignment_id)

    assignment_service.resume(a, today=today_for(a.user))
    session.add(a)
    session.commit()
    session.refresh(a)

    if a.user is not None and a.plan is not None and a.user.email:
        try:
            await mailer.send_plan_resumed(
                a.user.email, a.plan, a.end_date, actor=current_user
            )
        except Exception:
            pass

    return serialize_assignment(a)


@router.post(
    "/{assignment_id}/cancel",
    response_model=UserPlanAssignmentRead,
    response_model_exclude_none=True,
)
async def cancel_assignment(
    assignment_id: str,
    session: Session = Depends(get_session),
    mailer: Mailer = Depends(get_mailer),
    current_user: User = Depends(get_current_user),
) -> UserPlanAssignmentRead:
    a = get_or_404(session, assignment_id)
    assignment_service.cancel(a)
    session.add(a)
    session.commit()
    session.refresh(a)

    if a.user is not None and a.plan is not None and a.user.email:
        try:
            await mailer.send_plan_cancelled(a.user.email, a.plan, actor=current_user)
        except Exception:
            pass

    return serialize_assignment(a)


@router.post(
    "/{assignment_id}/restart",
    response_model=UserPlanAssignmentRead,
    response_model_exclude_none=True,
)
async def restart_assignment(
    assignment_id: str,
    session: Session = Depends(get_session),
    mailer: Mailer = Depends(get_mailer),
    current_user: User = Depends(get_current_user),
) -> UserPlanAssignmentRead:
    a = get_or_404(session, assignment_id)
    if a.plan is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot restart — the linked plan no longer exists.",
        )
    assignment_service.restart(a, a.plan, today=today_for(a.user))
    session.add(a)
    session.commit()
    session.refresh(a)

    if a.user is not None and a.user.email:
        try:
            await mailer.send_plan_restarted(
                a.user.email, a.plan, a.start_date, a.end_date, actor=current_user
            )
        except Exception:
            pass

    return serialize_assignment(a)


@router.get(
    "/{assignment_id}/schedule",
    response_model=List[ScheduleEntry],
    response_model_exclude_none=True,
)
def get_assignment_schedule(
    assignment_id: str,
    session: Session = Depends(get_session),
) -> List[ScheduleEntry]:

    a = get_or_404(session, assignment_id)
    return compute_schedule(a)


