from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from db import get_session
from models import User, UserPlanAssignmentStatus
from routers.deps import get_current_user
from schemas import (
    UserCreate,
    UserPlanAssignmentRead,
    UserRead,
    UserUpdate,
    serialize_assignment,
    serialize_user,
)
from services.auth import hash_password, revoke_all_for_user
from services.mailer import Mailer, get_mailer

router = APIRouter(tags=["users"])


def get_user_or_404(session: Session, user_id: str, *, allow_removed: bool = False) -> User:
    user = session.get(User, user_id)

    if not user or (user.removed and not allow_removed):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return user


@router.get("", response_model=List[UserRead], response_model_exclude_none=True)
def list_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> List[UserRead]:
    statement = (
        select(User)
        .where(User.id != current_user.id)
        .order_by(User.first_name)
    )
    rows = session.exec(statement).all()

    return [serialize_user(u) for u in rows]


@router.get("/{user_id}", response_model=UserRead, response_model_exclude_none=True)
def get_user(user_id: str, session: Session = Depends(get_session)) -> UserRead:
    user = get_user_or_404(session, user_id, allow_removed=True)

    return serialize_user(user)


@router.post("", response_model=UserRead, response_model_exclude_none=True, status_code=201)
async def create_user(
    payload: UserCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    mailer: Mailer = Depends(get_mailer),
) -> UserRead:
    existing = session.exec(select(User).where(User.email == payload.email)).first()

    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

    data = payload.model_dump(exclude={"password"})
    user = User(**data)
    if payload.password:
        user.password_hash = hash_password(payload.password)

    session.add(user)
    session.commit()
    session.refresh(user)

    try:
        await mailer.send_user_account_created(
            user.email, user.first_name, creator=current_user
        )
    except Exception:
        pass

    return serialize_user(user)


@router.patch("/{user_id}", response_model=UserRead, response_model_exclude_none=True)
def update_user(
    user_id: str,
    payload: UserUpdate,
    session: Session = Depends(get_session),
) -> UserRead:
    user = get_user_or_404(session, user_id)

    updates = payload.model_dump(exclude_unset=True)
    new_email = updates.get("email")

    if new_email and new_email != user.email:
        statement = select(User).where(User.email == new_email, User.id != user_id)
        clash = session.exec(statement).first()
        
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )

    for field, value in updates.items():
        setattr(user, field, value)

    session.add(user)
    session.commit()
    session.refresh(user)

    return serialize_user(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(user_id: str, session: Session = Depends(get_session)) -> None:
    user = get_user_or_404(session, user_id)
    user.removed = True

    session.add(user)
    session.commit()

    revoke_all_for_user(session, user.id)


@router.post(
    "/{user_id}/restore",
    response_model=UserRead,
    response_model_exclude_none=True,
)
def restore_user(user_id: str, session: Session = Depends(get_session)) -> UserRead:
    user = get_user_or_404(session, user_id, allow_removed=True)
    if user.removed:
        user.removed = False
        session.add(user)
        session.commit()
        session.refresh(user)
    return serialize_user(user)


@router.get(
    "/{user_id}/assignments",
    response_model=List[UserPlanAssignmentRead],
    response_model_exclude_none=True,
)
def list_user_assignments(
    user_id: str,
    session: Session = Depends(get_session),
) -> List[UserPlanAssignmentRead]:
    user = get_user_or_404(session, user_id, allow_removed=True)
    return [serialize_assignment(a) for a in user.assignments]


@router.get(
    "/{user_id}/current-assignment",
    response_model=UserPlanAssignmentRead,
    response_model_exclude_none=True,
)
def get_user_current_assignment(
    user_id: str,
    session: Session = Depends(get_session),
) -> UserPlanAssignmentRead:
    user = get_user_or_404(session, user_id, allow_removed=True)
    current_assignment = next(
        (a for a in user.assignments if a.status == UserPlanAssignmentStatus.in_progress),
        None,
    )
    if current_assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User has no current assignment")
    return serialize_assignment(current_assignment)
