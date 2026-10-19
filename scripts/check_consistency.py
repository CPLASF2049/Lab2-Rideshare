"""设计一致性自检：报告正文 ↔ 契约文件 ↔ 设计图。

检查项：
1. **事件**：`docs/design.md` §4.6 的事件表与 `contracts/events/events.md` 的事件清单一致；
   并有对应的 JSON 示例（示例中的 `event_type` 必须存在于事件清单中）。
2. **对外接口**：报告中出现的 `/v1/...` 路径都存在于三份 OpenAPI 中，反之亦然。
3. **内部接口**：proto 中的 `rpc` 方法都出现在报告 §4.5.3 的方法表中。
4. **服务名**：报告中出现的 `*-service` / `*-gateway` 都在 §2.2.1 的服务清单内。
5. **图**：报告引用的图片文件都存在。

用法：python scripts/check_consistency.py
退出码 0 = 一致；1 = 存在不一致（逐条打印）。
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from check_contracts import parse_yaml  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESIGN = os.path.join(ROOT, "docs", "design.md")
EVENTS_MD = os.path.join(ROOT, "contracts", "events", "events.md")

EVENT_RE = re.compile(r"`([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+\.v1)`")
PATH_RE = re.compile(r"`(/v1/[A-Za-z0-9_/{}\-]+)`")
RPC_RE = re.compile(r"^\s*rpc\s+(\w+)\s*\(", re.MULTILINE)
SERVICE_RE = re.compile(r"\b([a-z][a-z0-9]*-service|[a-z][a-z0-9]*-gateway)\b")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def normalize_path(path: str) -> str:
    """把 `{trip_id}` 与 `{id}` 等占位符统一，避免同一路径因参数名不同被判为不一致。"""
    return re.sub(r"\{[^}]*\}", "{}", path.rstrip("/"))


def main() -> int:
    design = read(DESIGN)
    events_md = read(EVENTS_MD)
    problems: list[str] = []

    # ---------------------------------------------------------------- 1. 事件
    # 排除包名（rideshare.*）与 Kafka topic 前缀（sh./hz./nj./all.），它们不是事件名
    design_events = {
        name
        for name in EVENT_RE.findall(design)
        if not re.match(r"^(rideshare|sh|hz|nj|all)\.", name)
    }
    catalog_events = set(re.findall(r"^\|\s*`([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+\.v1)`", events_md, re.MULTILINE))
    example_events = set()
    for path in glob.glob(os.path.join(ROOT, "contracts", "events", "examples", "*.json")):
        example_events.add(json.loads(read(path))["event_type"])

    missing_in_catalog = sorted(design_events - catalog_events)
    missing_in_design = sorted(catalog_events - design_events)
    if missing_in_catalog:
        problems.append(f"报告中出现但事件目录缺少：{missing_in_catalog}")
    if missing_in_design:
        problems.append(f"事件目录中有但报告未提及：{missing_in_design}")
    unknown_examples = sorted(example_events - catalog_events)
    if unknown_examples:
        problems.append(f"示例中的事件名不在事件目录里：{unknown_examples}")

    # ---------------------------------------------------------------- 2. 对外路径
    spec_paths: set[str] = set()
    for path in glob.glob(os.path.join(ROOT, "contracts", "openapi", "*.yaml")):
        doc = parse_yaml(read(path), os.path.basename(path))
        spec_paths |= {normalize_path(p) for p in (doc.get("paths") or {})}
    design_paths = {normalize_path(p) for p in PATH_RE.findall(design)}

    only_design = sorted(design_paths - spec_paths)
    only_spec = sorted(spec_paths - design_paths)
    if only_design:
        problems.append(f"报告中的路径未在 OpenAPI 中定义：{only_design}")
    if only_spec:
        problems.append(f"OpenAPI 中的路径未在报告接口表中出现：{only_spec}")

    # ---------------------------------------------------------------- 3. gRPC 方法
    rpc_methods: set[str] = set()
    for path in glob.glob(os.path.join(ROOT, "contracts", "proto", "*.proto")):
        rpc_methods |= set(RPC_RE.findall(read(path)))
    # 报告 §4.5.3 的方法以 `Method` 或 `` `Method` `` 形式出现在表格中
    section = design.split("#### 4.5.3", 1)[-1].split("### 4.6", 1)[0]
    missing_rpc = sorted(name for name in rpc_methods if name not in section)
    if missing_rpc:
        problems.append(f"proto 中的方法未在报告 §4.5.3 列出：{missing_rpc}")

    # ---------------------------------------------------------------- 4. 服务名
    declared = set(SERVICE_RE.findall(design.split("#### 2.2.1", 1)[1].split("#### 2.2.2", 1)[0]))
    used = set(SERVICE_RE.findall(design))
    undeclared = sorted(used - declared)
    if undeclared:
        problems.append(f"报告中使用了未在 §2.2.1 声明的服务名：{undeclared}")

    # ---------------------------------------------------------------- 5. 图片
    for relative in IMAGE_RE.findall(design):
        if relative.startswith("http"):
            continue
        target = os.path.normpath(os.path.join(os.path.dirname(DESIGN), relative))
        if not os.path.exists(target):
            problems.append(f"报告引用的图片不存在：{relative}")

    # ---------------------------------------------------------------- 输出
    print(f"事件：报告 {len(design_events)} 个 / 目录 {len(catalog_events)} 个 / 示例 {len(example_events)} 个")
    print(f"对外路径：报告 {len(design_paths)} 条 / OpenAPI {len(spec_paths)} 条")
    print(f"gRPC 方法：{len(rpc_methods)} 个")
    print(f"服务名：声明 {len(declared)} 个 / 使用 {len(used)} 个")

    if problems:
        print("\n发现不一致：")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\n一致性检查通过：报告、契约与设计图的名称完全对齐。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
