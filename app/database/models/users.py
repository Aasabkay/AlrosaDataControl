import enum

from sqlalchemy.orm import Mapped, mapped_column

from app.database.models.base import Base


class UsersRoles(str, enum.Enum):
    ADMIN = 'admin'
    USER = 'user'


class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(unique=True)
    hashed_password: Mapped[str]
    role: Mapped[str]
