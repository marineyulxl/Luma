"""导出或核对V1.0 业务契约，不加载数据库配置或连接数据库。"""

import argparse
import json
from pathlib import Path

from app.api.contract import record_contract

OUTPUT = Path(__file__).resolve().parents[2] / "docs/architecture/api/openapi.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = json.dumps(record_contract(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != data:
            raise SystemExit("契约产物与 Schema 不一致，请运行导出命令")
        print("契约产物一致")
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(data, encoding="utf-8")
    print("已导出V1.0 业务契约")


if __name__ == "__main__":
    main()
