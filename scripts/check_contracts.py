"""OpenAPI / YAML 子集校验器。

本仓库不引入第三方依赖（环境无网络），因此这里实现一个**够用的 YAML 子集解析器**，
并在此基础上做 OpenAPI 3.0 的结构与引用完整性检查：

1. YAML 语法：缩进必须是 2 的倍数、禁止 Tab、禁止重复键、块标量（`|`/`>`）正确收尾；
2. 解析结果：映射 / 序列 / 标量 / flow 序列（`[a, b]` / `{k: v}`）；
3. OpenAPI 检查：`paths` 以 `/` 开头、方法合法、每个 operation 有 `operationId`/`summary`/`responses`、
   `tags` 已声明、每个 `$ref` 都能在 `#/components/...` 中找到、`security` 引用的 scheme 存在。

用法：
    python scripts/check_contracts.py                # 校验 contracts/openapi/*.yaml
    python scripts/check_contracts.py file1.yaml ... # 校验指定文件
退出码 0 = 全部通过，1 = 存在问题。
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


class YamlError(Exception):
    pass


def _strip_comment(line: str) -> str:
    """去掉行内注释（保留引号内的 #）。"""
    out = []
    quote = None
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            out.append(ch)
            if ch == quote and (i == 0 or line[i - 1] != "\\"):
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            out.append(ch)
        elif ch == "#" and (not out or out[-1] in (" ", "\t")):
            break
        else:
            out.append(ch)
        i += 1
    return "".join(out).rstrip()


def _scalar(text: str):
    text = text.strip()
    if text == "":
        return None
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_scalar(part) for part in _split_flow(inner)]
    if text.startswith("{") and text.endswith("}"):
        inner = text[1:-1].strip()
        result = {}
        if not inner:
            return result
        for part in _split_flow(inner):
            if ":" not in part:
                raise YamlError(f"flow 映射项缺少冒号：{part!r}")
            key, _, value = part.partition(":")
            result[key.strip()] = _scalar(value)
        return result
    if text in ("null", "~", "Null", "NULL"):
        return None
    if text in ("true", "True", "TRUE"):
        return True
    if text in ("false", "False", "FALSE"):
        return False
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def _split_flow(text: str) -> list[str]:
    parts, depth, quote, cur = [], 0, None, []
    for ch in text:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            cur.append(ch)
        elif ch in "[{":
            depth += 1
            cur.append(ch)
        elif ch in "]}":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        parts.append("".join(cur))
    return [p.strip() for p in parts]


def parse_yaml(text: str, source: str = "<string>"):
    """解析 YAML 子集；返回 Python 对象。"""
    lines: list[tuple[int, str, int]] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlError(f"{source}:{lineno}: 缩进中使用 Tab")
        content = _strip_comment(raw)
        if not content.strip():
            continue
        indent = len(content) - len(content.lstrip(" "))
        if indent % 2 != 0:
            raise YamlError(f"{source}:{lineno}: 缩进不是 2 的倍数（{indent}）")
        lines.append((indent, content.strip(), lineno))

    pos = 0

    def parse_block(indent: int):
        nonlocal pos
        if pos >= len(lines):
            return None
        cur_indent, cur_text, _ = lines[pos]
        if cur_text.startswith("- "):
            return parse_seq(indent)
        return parse_map(indent)

    def parse_seq(indent: int):
        nonlocal pos
        items = []
        while pos < len(lines):
            cur_indent, cur_text, lineno = lines[pos]
            if cur_indent < indent:
                break
            if cur_indent != indent or not cur_text.startswith("- "):
                break
            rest = cur_text[2:].strip()
            pos += 1
            if rest == "":
                items.append(parse_block(indent + 2))
            elif re.match(r"^[^\s'\"]+\s*:(?!:)", rest) and not rest.startswith(("[", "{")):
                # 序列项本身是映射的起始行，例如 "- name: Quote"
                key, _, value = rest.partition(":")
                node: dict = {}
                if value.strip():
                    node[key.strip()] = _scalar(value)
                else:
                    node[key.strip()] = parse_block(indent + 4) if (
                        pos < len(lines) and lines[pos][0] > indent
                    ) else None
                while pos < len(lines) and lines[pos][0] == indent + 2 and not lines[pos][1].startswith("- "):
                    k2, _, v2 = lines[pos][1].partition(":")
                    pos += 1
                    if v2.strip():
                        node[k2.strip()] = _scalar(v2)
                    else:
                        node[k2.strip()] = parse_block(indent + 4) if (
                            pos < len(lines) and lines[pos][0] > indent + 2
                        ) else None
                items.append(node)
            else:
                items.append(_scalar(rest))
        return items

    def parse_map(indent: int):
        nonlocal pos
        node: dict = {}
        while pos < len(lines):
            cur_indent, cur_text, lineno = lines[pos]
            if cur_indent < indent:
                break
            if cur_indent > indent:
                raise YamlError(f"{source}:{lineno}: 意外缩进")
            if cur_text.startswith("- "):
                break
            if ":" not in cur_text:
                raise YamlError(f"{source}:{lineno}: 缺少冒号：{cur_text!r}")
            key, _, value = cur_text.partition(":")
            key = key.strip().strip("'\"")
            if key in node:
                raise YamlError(f"{source}:{lineno}: 重复键 {key!r}")
            value = value.strip()
            pos += 1
            if value in ("|", ">", "|-", ">-"):
                block = []
                while pos < len(lines) and lines[pos][0] > indent:
                    block.append(lines[pos][1])
                    pos += 1
                node[key] = "\n".join(block)
            elif value == "":
                if pos < len(lines) and (
                    lines[pos][0] > indent
                    or (lines[pos][0] == indent and lines[pos][1].startswith("- "))
                ):
                    child_indent = lines[pos][0]
                    node[key] = parse_block(child_indent)
                else:
                    node[key] = None
            elif value.startswith("&") or value.startswith("*"):
                node[key] = _scalar(value)
            else:
                node[key] = _scalar(value)
        return node

    result = parse_block(lines[0][0] if lines else 0)
    if pos != len(lines):
        raise YamlError(f"{source}:{lines[pos][2]}: 无法解析的内容：{lines[pos][1]!r}")
    return result


def _walk_refs(node, path=""):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield path, value
            else:
                yield from _walk_refs(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk_refs(value, f"{path}[{index}]")


def _resolve_pointer(doc, ref: str):
    if not ref.startswith("#/"):
        return None  # 外部引用不在本次校验范围内
    cur = doc
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict) and token in cur:
            cur = cur[token]
        elif isinstance(cur, list) and token.isdigit() and int(token) < len(cur):
            cur = cur[int(token)]
        else:
            return None
    return cur


def check_openapi(doc, source: str) -> list[str]:
    problems: list[str] = []
    if not isinstance(doc, dict):
        return [f"{source}: 根节点必须是映射"]
    if not str(doc.get("openapi", "")).startswith("3."):
        problems.append(f"{source}: 缺少 openapi: 3.x")
    for field in ("info", "paths"):
        if field not in doc:
            problems.append(f"{source}: 缺少顶层字段 {field}")

    tags = {t.get("name") for t in (doc.get("tags") or []) if isinstance(t, dict)}
    schemes = set(((doc.get("components") or {}).get("securitySchemes") or {}).keys())

    paths = doc.get("paths") or {}
    if not isinstance(paths, dict) or not paths:
        problems.append(f"{source}: paths 为空")
    operation_ids = set()
    for path, item in paths.items():
        if not str(path).startswith("/"):
            problems.append(f"{source}: 路径必须以 / 开头：{path}")
        if not isinstance(item, dict):
            problems.append(f"{source}: 路径 {path} 的内容必须是映射")
            continue
        for method, operation in item.items():
            if method == "parameters":
                continue
            if method not in HTTP_METHODS:
                problems.append(f"{source}: {path} 下有未知方法 {method}")
                continue
            if not isinstance(operation, dict):
                problems.append(f"{source}: {path} {method} 必须是映射")
                continue
            op_id = operation.get("operationId")
            if not op_id:
                problems.append(f"{source}: {path} {method} 缺少 operationId")
            elif op_id in operation_ids:
                problems.append(f"{source}: operationId 重复：{op_id}")
            else:
                operation_ids.add(op_id)
            if not operation.get("summary"):
                problems.append(f"{source}: {path} {method} 缺少 summary")
            responses = operation.get("responses")
            if not isinstance(responses, dict) or not responses:
                problems.append(f"{source}: {path} {method} 缺少 responses")
            else:
                for code in responses:
                    if not re.fullmatch(r"\d{3}|default|[1-5]XX", str(code)):
                        problems.append(f"{source}: {path} {method} 状态码非法：{code}")
            for tag in operation.get("tags") or []:
                if tag not in tags:
                    problems.append(f"{source}: {path} {method} 使用了未声明的 tag：{tag}")

    for root_security in doc.get("security") or []:
        for scheme in root_security:
            if scheme not in schemes:
                problems.append(f"{source}: security 引用了未定义的 scheme：{scheme}")

    for where, ref in _walk_refs(doc):
        if _resolve_pointer(doc, ref) is None:
            problems.append(f"{source}: {where} 的 $ref 无法解析：{ref}")
    return problems


def main(argv: list[str]) -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    targets = argv[1:] or sorted(glob.glob(os.path.join(root, "contracts", "openapi", "*.yaml")))
    if not targets:
        print("没有找到待校验文件")
        return 1

    failed = 0
    for target in targets:
        with open(target, encoding="utf-8") as handle:
            text = handle.read()
        try:
            doc = parse_yaml(text, os.path.basename(target))
        except YamlError as error:
            print(f"[FAIL] {error}")
            failed += 1
            continue
        problems = check_openapi(doc, os.path.basename(target))
        if problems:
            failed += 1
            for problem in problems:
                print(f"[FAIL] {problem}")
        else:
            path_count = len(doc.get("paths") or {})
            schema_count = len(((doc.get("components") or {}).get("schemas") or {}))
            print(f"[ OK ] {os.path.basename(target)}: {path_count} 个路径, {schema_count} 个 schema")

    # 额外自检：把解析结果序列化为 JSON，确认结构可完整遍历
    for target in targets:
        try:
            with open(target, encoding="utf-8") as handle:
                json.dumps(parse_yaml(handle.read(), os.path.basename(target)), ensure_ascii=False)
        except Exception as error:  # noqa: BLE001
            print(f"[FAIL] {target}: 无法序列化 -> {error}")
            failed += 1

    print("通过" if failed == 0 else f"{failed} 个文件存在问题")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
