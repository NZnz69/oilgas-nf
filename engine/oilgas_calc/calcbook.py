# -*- coding: utf-8 -*-
"""计算书生成模块（闸门四：结果必带计算书）。

每个计算结果都输出统一结构的计算书，任何人可按计算书手工复算：
  输入（含单位换算）→ 公式（含溯源状态）→ 常数（含来源）
  → 中间量 → 结果（合理有效位数）→ 判据对照（知识库状态）→ 告警。
"""

import datetime
import json
import os

ENGINE_VERSION = "0.1.0"

# 判据知识库路径：由环境变量 NF_KNOWLEDGE_DIR 指向 Skill 的 references 目录。
# 未设置或文件不存在时，判据状态一律返回「未收录」——白盒行为，绝不硬造区间。
_JUDGES_RELATIVE = os.path.join("formulas", "judges.json")


def _load_judges():
    """读取已校核转正的判据卡片数据（JSON）。未收录返回空 dict。"""
    root = os.environ.get("NF_KNOWLEDGE_DIR")
    if not root:
        return {}
    path = os.path.join(root, _JUDGES_RELATIVE)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def new_calcbook(tool_name):
    """创建一份空白计算书骨架。"""
    return {
        "engine_version": ENGINE_VERSION,
        "tool": tool_name,
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "inputs": [],
        "formulas": [],
        "constants": [],
        "intermediates": [],
        "results": [],
        "judgements": [],
        "judgement": None,
        "warnings": [],
    }


def add_input(book, name, value, unit, si_value, si_unit, dimension, source="user"):
    book["inputs"].append({
        "name": name, "value": value, "unit": unit,
        "si_value": round(si_value, 10), "si_unit": si_unit,
        "dimension": dimension, "source": source,
    })


def add_formula(book, name, expression, reference, status="待校核", card=None):
    """登记公式。reference 注明出处；status 反映公式卡片收录状态。"""
    book["formulas"].append({
        "name": name, "expression": expression,
        "reference": {"source": reference, "status": status, "card": card},
    })


def add_constant(book, name, value, unit, source):
    book["constants"].append({"name": name, "value": value, "unit": unit, "source": source})


def add_intermediate(book, name, value, unit, note=""):
    book["intermediates"].append({
        "name": name, "value": _round_sig(value), "unit": unit, "note": note,
    })


def add_result(book, name, value, unit, note=""):
    book["results"].append({
        "name": name, "value": _round_sig(value), "unit": unit, "note": note,
    })


def add_warning(book, message):
    book["warnings"].append(message)


def set_judgement(book, subject, value=None, unit=None):
    """对照知识库判据（v0.1.1 起支持多判据追加，不再互相覆盖）。

    无卡片时如实返回未收录，绝不输出编造的区间结论。
    每次调用追加一条到 book["judgements"]；book["judgement"] 保留
    最后一条以兼容旧读取方。
    """
    judges = _load_judges()
    entry = judges.get(subject)
    if not entry:
        record = {
            "subject": subject, "status": "未收录",
            "note": "合理区间判据卡片未收录（知识库为空或该判据未转正），本次不判定；请补充公式/判据卡片并经人工校核。",
        }
    else:
        # 判据卡片已收录：按区间判定
        lo, hi = entry.get("lower"), entry.get("upper")
        status = "无法判定"
        if value is not None and lo is not None and hi is not None:
            if value < lo:
                status = "低于工程合理区间"
            elif value > hi:
                status = "高于工程合理区间"
            else:
                status = "在工程合理区间内"
        record = {
            "subject": subject, "value": _round_sig(value) if value is not None else None,
            "unit": unit, "lower": lo, "upper": hi, "status": status,
            "source": entry.get("source", ""), "card_status": entry.get("status", "待校核"),
        }
    book.setdefault("judgements", []).append(record)
    book["judgement"] = record  # 兼容字段：保留最后一条


def _round_sig(x, sig=6):
    """按有效位数舍入（默认 6 位），避免虚假精确。"""
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return x
    if x == 0 or not isinstance(x, float):
        return round(x, 6)
    from decimal import Decimal
    d = Decimal(repr(x))
    return float(round(d, sig))


def finalize(book):
    """计算书收尾：序列化为 JSON 字符串（保留中文可读性）。"""
    return json.dumps(book, ensure_ascii=False, indent=2)
