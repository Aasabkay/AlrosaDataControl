"""Создание администратора. Запуск: python -m tools.create_admin_user"""

import asyncio
from getpass import getpass

from app.api.helpers import hash_password
from app.database.models import Users
from app.database.models.users import UsersRoles
from app.database.repositories.users import check_user_exists, add_user
from app.database.session import SessionLocal


async def create_admin():
    login = input("Введите логин: ")
    password = getpass("Введите пароль: ")

    async with SessionLocal() as session:
        if await check_user_exists(session, login):
            print("Пользователь с таким именем уже существует")
            return False

        user = Users(login=login, hashed_password=hash_password(password),
                     role=UsersRoles.ADMIN.value)
        user_id, user_role = await add_user(session, user)

    print(f"Администратор был успешно добавлен: ID: {user_id}, ROLE: {user_role}")
    return True


if __name__ == '__main__':
    try:
        asyncio.run(create_admin())
    except KeyboardInterrupt:
        pass
