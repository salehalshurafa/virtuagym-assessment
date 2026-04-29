from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from db import get_session
from models import WeeklySplitTemplate, WeeklyWorkoutPlan
from schemas import (
    WeeklySplitTemplateCreate,
    WeeklySplitTemplateFromWeeklyPlanRequest,
    WeeklySplitTemplateRead,
    WeeklySplitTemplateUpdate,
)
from services.template_service import (
    cascade_library_exercises_for_week,
    serialize_weekly_to_template_json,
)

router = APIRouter(tags=["weekly-split-templates"])


def get_or_404(session: Session, template_id: str) -> WeeklySplitTemplate:
    row = session.get(WeeklySplitTemplate, template_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Weekly split template not found",
        )
    return row


def to_read(row: WeeklySplitTemplate) -> WeeklySplitTemplateRead:
    return WeeklySplitTemplateRead(
        id=row.id,
        label=row.label,
        days=row.days or [],
    )


@router.get(
    "", response_model=List[WeeklySplitTemplateRead], response_model_exclude_none=True
)
def list_templates(
    session: Session = Depends(get_session),
) -> List[WeeklySplitTemplateRead]:
    rows = session.exec(
        select(WeeklySplitTemplate).order_by(WeeklySplitTemplate.label)
    ).all()
    return [to_read(r) for r in rows]


@router.get(
    "/{template_id}",
    response_model=WeeklySplitTemplateRead,
    response_model_exclude_none=True,
)
def get_template(
    template_id: str, session: Session = Depends(get_session)
) -> WeeklySplitTemplateRead:
    return to_read(get_or_404(session, template_id))


@router.post(
    "",
    response_model=WeeklySplitTemplateRead,
    response_model_exclude_none=True,
    status_code=201,
)
def create_template(
    payload: WeeklySplitTemplateCreate, session: Session = Depends(get_session)
) -> WeeklySplitTemplateRead:
    existing = session.exec(
        select(WeeklySplitTemplate).where(WeeklySplitTemplate.label == payload.label)
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A weekly split template labelled '{payload.label}' already exists",
        )

    row = WeeklySplitTemplate(
        label=payload.label,
        days=[d.model_dump(by_alias=True) for d in payload.days],
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return to_read(row)


@router.patch(
    "/{template_id}",
    response_model=WeeklySplitTemplateRead,
    response_model_exclude_none=True,
)
def update_template(
    template_id: str,
    payload: WeeklySplitTemplateUpdate,
    session: Session = Depends(get_session),
) -> WeeklySplitTemplateRead:
    row = get_or_404(session, template_id)

    updates = payload.model_dump(exclude_unset=True, by_alias=False)
    days = updates.pop("days", "MISSING")

    new_label = updates.get("label")
    if new_label and new_label != row.label:
        clash = session.exec(
            select(WeeklySplitTemplate)
            .where(WeeklySplitTemplate.label == new_label)
            .where(WeeklySplitTemplate.id != template_id)
        ).first()
        if clash is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A weekly split template labelled '{new_label}' already exists",
            )

    for field, value in updates.items():
        setattr(row, field, value)

    if days != "MISSING":
        row.days = (
            [d if isinstance(d, dict) else d.model_dump(by_alias=True) for d in days]
            if days
            else []
        )

    session.add(row)
    session.commit()
    session.refresh(row)
    return to_read(row)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: str, session: Session = Depends(get_session)
) -> None:
    row = get_or_404(session, template_id)
    session.delete(row)
    session.commit()


@router.post(
    "/from-weekly-plan",
    response_model=WeeklySplitTemplateRead,
    response_model_exclude_none=True,
    status_code=201,
)
def template_from_weekly_plan(
    payload: WeeklySplitTemplateFromWeeklyPlanRequest,
    session: Session = Depends(get_session),
) -> WeeklySplitTemplateRead:
    weekly = session.get(WeeklyWorkoutPlan, payload.weekly_plan_id)
    if weekly is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Weekly plan not found"
        )

    label = (payload.label or weekly.label).strip()
    if not label:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template label cannot be empty",
        )
    clash = session.exec(
        select(WeeklySplitTemplate).where(WeeklySplitTemplate.label == label)
    ).first()
    if clash is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A weekly split template labelled '{label}' already exists",
        )

    days_json = serialize_weekly_to_template_json(weekly)
    cascade_library_exercises_for_week(session, weekly)

    row = WeeklySplitTemplate(label=label, days=days_json)
    session.add(row)
    session.commit()
    session.refresh(row)
    return to_read(row)
