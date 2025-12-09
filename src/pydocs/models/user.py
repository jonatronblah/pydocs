import uuid
from typing import Optional

from fastapi import Request
from fastapi_users import BaseUserManager, UUIDIDMixin, schemas

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import String

from .base import Base

from fastapi_users.exceptions import UserAlreadyExists


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "appuser"

    username: Mapped[str] = mapped_column(String(length=200))
    """Represents a user entity."""


class UserRead(schemas.BaseUser[uuid.UUID]):
    username: str
    """Represents a read command for a user."""


class UserCreate(schemas.BaseUserCreate):
    username: str
    """Represents a create command for a user."""


class UserUpdate(schemas.BaseUserUpdate):
    username: str
    """Represents an update command for a user."""


SECRET = "SECRET"


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")


# class User(Base):
#     __tablename__ = "users"
#     id = Column(String, primary_key=True)
#     email = Column(String, unique=True, nullable=False)
#     full_name = Column(String, nullable=False)

#     @classmethod
#     async def create(cls, db: AsyncSession, id=None, **kwargs):
#         if not id:
#             id = uuid4().hex

#         transaction = cls(id=id, **kwargs)
#         db.add(transaction)
#         await db.commit()
#         await db.refresh(transaction)
#         return transaction

#     @classmethod
#     async def get(cls, db: AsyncSession, id: str):
#         try:
#             transaction = await db.get(cls, id)
#         except NoResultFound:
#             return None
#         return transaction

#     @classmethod
#     async def get_all(cls, db: AsyncSession):
#         return (await db.execute(select(cls))).scalars().all()
