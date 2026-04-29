from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from db import get_session
from models import Exercise
from schemas import ExerciseCreate, ExerciseRead, ExerciseUpdate

router = APIRouter(tags=["exercises"])


def get_or_404(session: Session, exercise_id: str) -> Exercise:
    ex = session.get(Exercise, exercise_id)
    if ex is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return ex


@router.get("", response_model=List[ExerciseRead], response_model_exclude_none=True)
def list_exercises(session: Session = Depends(get_session)) -> List[ExerciseRead]:
    rows = session.exec(
        select(Exercise).order_by(Exercise.usage_count.desc(), Exercise.name)
    ).all()
    return [ExerciseRead.model_validate(r) for r in rows]


@router.get("/{exercise_id}", response_model=ExerciseRead, response_model_exclude_none=True)
def get_exercise(exercise_id: str, session: Session = Depends(get_session)) -> ExerciseRead:
    return ExerciseRead.model_validate(get_or_404(session, exercise_id))


@router.post("", response_model=ExerciseRead, response_model_exclude_none=True, status_code=201)
def create_exercise(
    payload: ExerciseCreate, session: Session = Depends(get_session)
) -> ExerciseRead:
    ex = Exercise(**payload.model_dump())
    session.add(ex)
    session.commit()
    session.refresh(ex)
    return ExerciseRead.model_validate(ex)


@router.patch("/{exercise_id}", response_model=ExerciseRead, response_model_exclude_none=True)
def update_exercise(
    exercise_id: str,
    payload: ExerciseUpdate,
    session: Session = Depends(get_session),
) -> ExerciseRead:
    ex = get_or_404(session, exercise_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ex, field, value)
    session.add(ex)
    session.commit()
    session.refresh(ex)
    return ExerciseRead.model_validate(ex)


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: str, session: Session = Depends(get_session)) -> None:
    ex = get_or_404(session, exercise_id)
    session.delete(ex)
    session.commit()
