from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status

from app.api.dependencies import sessionDepends
from app.api.helpers import hash_password, verify_password, create_access_token
from app.api.schemas import UserRegister, Token
from app.database.models import Users
from app.database.models.users import UsersRoles
from app.database.repositories.users import check_user_exists, add_user, get_user

auth_router = APIRouter()

@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegister, session: sessionDepends):
    if await check_user_exists(session, user_data.login):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")


    hashed_pass = hash_password(user_data.password)
    user = Users(login=user_data.login, hashed_password=hashed_pass, role=UsersRoles.USER.value)

    user_id, user_role = await add_user(session, user)
    return {"user_id": user_id, "user_role": user_role}

@auth_router.post("/login", status_code=status.HTTP_200_OK, response_model=Token)
async def login(session: sessionDepends, form_data: OAuth2PasswordRequestForm = Depends()):
    # OAuth2PasswordRequestForm (form-data username/password) — чтобы работала
    # кнопка Authorize в Swagger UI
    user = await get_user(session=session, login=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect login or password")

    access_token = create_access_token(user.id, user.role)

    return Token(access_token=access_token, token_type="bearer")