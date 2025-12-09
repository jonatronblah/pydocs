from fastapi import APIRouter, Depends

from pydocs.models.user import UserCreate, UserRead, UserUpdate
from pydocs.database import current_active_user, api_users, auth_jwt

router = APIRouter()

current_superuser = api_users.current_user(superuser=True)


router.include_router(
    api_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(current_superuser)],
)

# router.include_router(
#     api_users.get_register_router(on_after_register),
#     prefix="/auth",
#     tags=["auth"],
#     dependencies=[Depends(current_superuser)],
# )


router.include_router(
    api_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

router.include_router(
    api_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)

router.include_router(
    api_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)
router.include_router(
    api_users.get_auth_router(auth_jwt),
    prefix="/auth/jwt",
    tags=["auth"],
)
