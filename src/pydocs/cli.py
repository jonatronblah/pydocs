import contextlib

from pydocs.database import sessionmanager, get_user_db, get_user_manager
from pydocs.config import settings
from pydocs.schema.user import UserCreate
from fastapi_users.exceptions import UserAlreadyExists


sessionmanager.init(settings.DATABASE_URL)

get_async_session_context = sessionmanager.session()
get_user_db_context = contextlib.asynccontextmanager(get_user_db)
get_user_manager_context = contextlib.asynccontextmanager(get_user_manager)


async def create_user(
    username: str, email: str, password: str, is_superuser: bool = False
):
    try:
        async with get_async_session_context as session:
            async with get_user_db_context(session) as user_db:
                async with get_user_manager_context(user_db) as user_manager:
                    user = await user_manager.create(
                        UserCreate(
                            username=username,
                            email=email,
                            password=password,
                            is_superuser=is_superuser,
                        )
                    )
                    print(f"User created {user}")
                    return user
    except UserAlreadyExists:
        print(f"User {email} already exists")
        raise
