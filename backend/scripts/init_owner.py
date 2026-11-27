"""通过交互式密码输入初始化单个所有者账号。"""

import argparse
import sys
import warnings
from getpass import GetPassWarning, getpass

from pydantic import SecretStr, ValidationError
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import ConfigurationError, Settings
from app.db.session import build_engine, build_session_factory
from app.modules.accounts.schemas import OwnerCreate
from app.modules.accounts.service import OwnerAlreadyInitializedError, initialize_owner


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化灵脑所有者账号，密码通过隐藏输入提供")
    parser.add_argument("--username", help="登录账号，不含空白字符")
    parser.add_argument("--display-name", help="界面显示名称")
    args = parser.parse_args()
    engine: Engine | None = None
    try:
        settings = Settings.load()
        username = args.username if args.username is not None else input("登录账号：")
        display_name = args.display_name if args.display_name is not None else input("显示名称：")
        with warnings.catch_warnings():
            # 无法隐藏输入时直接停止，避免 getpass 降级为可回显输入。
            warnings.simplefilter("error", GetPassWarning)
            password = getpass("密码：")
            confirmation = getpass("再次输入密码：")
        if password != confirmation:
            print("两次密码不一致，请重新运行。", file=sys.stderr)
            return 2
        request = OwnerCreate(
            username=username, display_name=display_name, password=SecretStr(password)
        )
        engine = build_engine(settings)
        owner = initialize_owner(build_session_factory(engine), request)
    except ValidationError as error:
        for detail in error.errors(include_input=False, include_url=False):
            field = ".".join(str(part) for part in detail["loc"])
            print(f"输入不符合要求（{field}）：{detail['msg']}", file=sys.stderr)
        return 2
    except OwnerAlreadyInitializedError as error:
        print(str(error), file=sys.stderr)
        return 1
    except ConfigurationError as error:
        print(str(error), file=sys.stderr)
        return 1
    except GetPassWarning:
        print("当前终端无法隐藏密码输入，请在交互式终端运行。", file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("初始化已取消。", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print("数据库操作失败，请检查连接与迁移状态后重试。", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    print(f"所有者账号已创建，登录账号为 {owner.username}，用户ID为 {owner.id}。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
