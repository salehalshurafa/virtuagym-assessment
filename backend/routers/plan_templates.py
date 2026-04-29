from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from db import get_session
from models import Plan, PlanTemplate
from schemas import (
    PlanTemplateCreate,
    PlanTemplateFromPlanRequest,
    PlanTemplateRead,
    PlanTemplateUpdate,
)
from services.template_service import serialize_plan_to_template_json

router = APIRouter(tags=["plan-templates"])


def get_or_404(session: Session, template_id: str) -> PlanTemplate:
    row = session.get(PlanTemplate, template_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan template not found"
        )
    return row


def to_read(row: PlanTemplate) -> PlanTemplateRead:
    return PlanTemplateRead(
        id=row.id,
        title=row.title,
        duration=row.duration,
        duration_type=row.duration_type,
        image_url=row.image_url,
        workout_days_per_week=row.workout_days_per_week,
        archived=row.archived,
        weekly_plans=row.weekly_plans,
        flat_days=row.flat_days,
    )


@router.get("", response_model=List[PlanTemplateRead], response_model_exclude_none=True)
def list_templates(
    include_archived: bool = False,
    session: Session = Depends(get_session),
) -> List[PlanTemplateRead]:
    statement = select(PlanTemplate)
    if not include_archived:
        statement = statement.where(PlanTemplate.archived == False)  # noqa: E712
    statement = statement.order_by(PlanTemplate.title)
    return [to_read(r) for r in session.exec(statement).all()]


@router.get(
    "/{template_id}",
    response_model=PlanTemplateRead,
    response_model_exclude_none=True,
)
def get_template(
    template_id: str, session: Session = Depends(get_session)
) -> PlanTemplateRead:
    return to_read(get_or_404(session, template_id))


@router.post(
    "",
    response_model=PlanTemplateRead,
    response_model_exclude_none=True,
    status_code=201,
)
def create_template(
    payload: PlanTemplateCreate, session: Session = Depends(get_session)
) -> PlanTemplateRead:
    if payload.weekly_plans and payload.flat_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pick exactly one of weeklyPlans or flatDays",
        )
    existing = session.exec(
        select(PlanTemplate).where(PlanTemplate.title == payload.title)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A plan template named '{payload.title}' already exists",
        )

    row = PlanTemplate(
        title=payload.title,
        duration=payload.duration,
        duration_type=payload.duration_type,
        image_url=payload.image_url,
        workout_days_per_week=payload.workout_days_per_week,
        weekly_plans=(
            [w.model_dump(by_alias=True) for w in payload.weekly_plans]
            if payload.weekly_plans
            else None
        ),
        flat_days=(
            [d.model_dump(by_alias=True) for d in payload.flat_days]
            if payload.flat_days
            else None
        ),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return to_read(row)


@router.patch(
    "/{template_id}",
    response_model=PlanTemplateRead,
    response_model_exclude_none=True,
)
def update_template(
    template_id: str,
    payload: PlanTemplateUpdate,
    session: Session = Depends(get_session),
) -> PlanTemplateRead:
    row = get_or_404(session, template_id)

    updates = payload.model_dump(exclude_unset=True, by_alias=False)
    weekly = updates.pop("weekly_plans", "MISSING")
    flat = updates.pop("flat_days", "MISSING")

    new_title = updates.get("title")
    if new_title and new_title != row.title:
        clash = session.exec(
            select(PlanTemplate)
            .where(PlanTemplate.title == new_title)
            .where(PlanTemplate.id != template_id)
        ).first()
        if clash is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A plan template named '{new_title}' already exists",
            )

    for field, value in updates.items():
        setattr(row, field, value)

    if weekly != "MISSING":
        row.weekly_plans = (
            [w if isinstance(w, dict) else w.model_dump(by_alias=True) for w in weekly]
            if weekly
            else None
        )
    if flat != "MISSING":
        row.flat_days = (
            [d if isinstance(d, dict) else d.model_dump(by_alias=True) for d in flat]
            if flat
            else None
        )

    session.add(row)
    session.commit()
    session.refresh(row)
    return to_read(row)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_template(
    template_id: str, session: Session = Depends(get_session)
) -> None:
    row = get_or_404(session, template_id)
    if row.archived:
        return
    row.archived = True
    session.add(row)
    session.commit()


@router.post(
    "/from-plan",
    response_model=PlanTemplateRead,
    response_model_exclude_none=True,
    status_code=201,
)
def template_from_plan(
    payload: PlanTemplateFromPlanRequest,
    session: Session = Depends(get_session),
) -> PlanTemplateRead:
    plan = session.get(Plan, payload.plan_id)
    if plan is None or plan.archived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )

    title = (payload.title or plan.title).strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template title cannot be empty",
        )
    clash = session.exec(
        select(PlanTemplate).where(PlanTemplate.title == title)
    ).first()
    if clash is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A plan template named '{title}' already exists",
        )

    nested = serialize_plan_to_template_json(plan)
    row = PlanTemplate(
        title=title,
        duration=plan.duration,
        duration_type=plan.duration_type,
        image_url=plan.image_url,
        workout_days_per_week=plan.workout_days_per_week,
        weekly_plans=nested.get("weekly_plans"),
        flat_days=nested.get("flat_days"),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return to_read(row)
