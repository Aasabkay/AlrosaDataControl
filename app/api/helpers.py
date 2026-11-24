from datetime import datetime, timezone, timedelta

import pwdlib
from fastapi import HTTPException
from fastapi.params import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pwdlib.hashers.argon2 import Argon2Hasher
from starlette import status

from app.config import JWT_SECRET
from app.database.models import Users
from app.database.repositories.users import get_user
from app.database.session import get_session

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = pwdlib.PasswordHash((Argon2Hasher(),))
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: int, user_role: str) -> str:
    expires_in = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {"sub": str(user_id), "role": user_role, "exp": expires_in}
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme),
                           session = Depends(get_session)) -> Users:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"})

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = int(payload['sub'])
    except (JWTError, KeyError, ValueError):
        raise credentials_exception

    user = await get_user(session=session, user_id=user_id)
    if not user:
        raise credentials_exception
    return user

def require_role(*allowed_roles: str):
    def check_role(current_user = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

        return current_user

    return check_role
