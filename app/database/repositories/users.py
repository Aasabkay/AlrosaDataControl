from sqlalchemy import select, delete, exists
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Users


async def add_user(session: AsyncSession, user_data: Users):
    session.add(user_data)
    await session.commit()
    await session.refresh(user_data)
    return user_data.id, user_data.role


async def get_user(*, session: AsyncSession,
                   login: str | None = None,
                   user_id: int | None = None) -> Users | None:
    if login:
        query = select(Users).where(Users.login == login)
    elif user_id:
        query = select(Users).where(Users.id == user_id)
    else:
        return None

    user_data = await session.execute(query)
    return user_data.scalar_one_or_none()


async def check_user_exists(session: AsyncSession, login: str) -> bool:
    query = select(exists().where(Users.login == login))

    return await session.scalar(query)


async def delete_user(session: AsyncSession, user_id: int):
    query = delete(Users).where(Users.id == user_id)
    deleted = await session.execute(query)
    await session.commit()
    return deleted.rowcount > 0


async def get_all_users(session: AsyncSession) -> list[Users]:
    query = select(Users)
    users = await session.execute(query)
    return users.scalars().all()
