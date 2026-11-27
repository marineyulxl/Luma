"""账号业务用例，数据库写入通过显式事务提交。"""

from dataclasses import dataclass
from uuid import UUID

from pwdlib import PasswordHash
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import transaction
from app.modules.accounts.models import User
from app.modules.accounts.schemas import OwnerCreate


class OwnerAlreadyInitializedError(Exception):
    """已有用户时拒绝重新初始化。"""


@dataclass(frozen=True)
class OwnerCreated:
    id: UUID
    username: str
    display_name: str


def initialize_owner(factory: sessionmaker[Session], request: OwnerCreate) -> OwnerCreated:
    # 哈希计算在事务外完成，避免在占用数据库锁时执行耗时运算。
    password_hash = PasswordHash.recommended().hash(request.password.get_secret_value())
    with transaction(factory) as session:
        # 空表没有可锁定的用户行。表锁让并发初始化依次检查单所有者条件。
        session.execute(text("LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE"))
        if session.scalar(select(User.id).limit(1)) is not None:
            raise OwnerAlreadyInitializedError("已有用户，不能重复初始化所有者账号")
        owner = User(
            username=request.username,
            display_name=request.display_name,
            password_hash=password_hash,
        )
        session.add(owner)
        session.flush()
        created = OwnerCreated(owner.id, owner.username, owner.display_name)
    return created
