"""仅对无业务数据的本地 luma_dev 验证迁移升降级。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, inspect, select

from app.db.config import database_url
from app.db.models import Base


def main() -> None:
    url = database_url()
    if url.database != "luma_dev" or url.host not in {"localhost", "127.0.0.1"}:
        raise SystemExit("只允许验证本地 luma_dev")
    engine = create_engine(url)
    with engine.connect() as conn:
        tables = set(inspect(conn).get_table_names())
        if tables - set(Base.metadata.tables) - {"alembic_version"}:
            raise SystemExit("存在非项目表，停止回退")
        for table in Base.metadata.tables.values():
            if table.name in tables and conn.scalar(select(func.count()).select_from(table)):
                raise SystemExit("存在业务数据，停止回退")
    engine.dispose()
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    command.check(cfg)
    print("迁移回退、重建及模型一致性检查通过")


if __name__ == "__main__":
    main()
