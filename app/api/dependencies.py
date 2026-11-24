from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.helpers import require_role
from app.database.models.users import UsersRoles
from app.database.session import get_session

sessionDepends = Annotated[AsyncSession, Depends(get_session)]

roleDepends = Depends(require_role(UsersRoles.ADMIN.value, UsersRoles.USER.value))
