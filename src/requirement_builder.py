#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""客户需求结构化：原始诉求 -> 需求说明书草稿。

把客户原始诉求结构化为需求点，再装配成需求说明书草稿，
覆盖 IaaS/PaaS/DAAS/MASS/SaaS 五层产品的需求收集与市场反馈整理。

## 三条不可让步的纪律

1. **每个需求点可追溯到原始诉求** —— 记录命中的原文片段与字符位置。
   写不出出处的需求点是编的。
2. **缺字段标「待补充」或「未提取到」，不瞎填** —— 尤其**期望指标不编数字**。
3. **业务场景描述缺失即拒绝生成说明书** —— 缺了它说明书就是空壳，
   生成一份空壳比不生成更糟。
"""
from __future__ import annotations

import re

# ---- A-01 登记的需求点分类规则（顺序即优先级，多标签）----
REQUIREMENT_RULES = [
    ("scheduling", r"排队|等待时间|调度|队列|作业等待"),
    ("compliance", r"政企|涉密|机房|不上公有云|数据不出|合规|自主可控|全国产"),
    ("competitor", r"对标|友商|华为|阿里|腾讯|百度|比较|友商"),
    ("migration", r"上云|迁移|统一管|放到云上|搬迁|纳管"),
    ("ops_efficiency", r"管理麻烦|运维|效率|不好管|混乱|难管理"),
    ("cost", r"贵|降本|预算|成本压|便宜"),
    ("performance", r"慢|卡顿|性能|不够快|延迟高"),
    ("sla", r"SLA|可用性|稳定性|不能挂|不能断"),
]

REQUIREMENT_LABEL = {
    "scheduling": "作业调度效率",
    "compliance": "合规与数据驻留",
    "competitor": "竞品认知",
    "migration": "资源迁移纳管",
    "ops_efficiency": "运维管理效率",
    "cost": "成本",
    "performance": "性能",
    "sla": "服务等级",
}

# A-02 登记的必填字段
REQUIRED_FIELDS = ["customer_industry", "scenario", "requirement_points",
                   "constraints", "priority", "expected_metrics"]

FIELD_LABEL = {
    "customer_industry": "客户行业",
    "scenario": "业务场景描述",
    "requirement_points": "需求点清单",
    "constraints": "约束条件",
    "priority": "优先级",
    "expected_metrics": "期望指标",
    "data_residency": "数据驻留要求",
}

PENDING = "待补充"
NOT_FOUND = "未提取到"


class RequirementError(Exception):
    pass


def classify(text: str) -> list[dict]:
    """把原始诉求拆成需求点，每个需求点带原文出处。"""
    points = []
    for label, pattern in REQUIREMENT_RULES:
        m = re.search(pattern, text, re.I)
        if not m:
            continue
        # 同一需求点可能多次出现，取全部命中位置以便复核
        spans = [(x.start(), x.end(), x.group(0)) for x in re.finditer(pattern, text, re.I)]
        points.append({
            "id": "RP-%02d" % (len(points) + 1),
            "label": label,
            "label_cn": REQUIREMENT_LABEL[label],
            "evidence": [{"quote": q, "start": s, "end": e} for s, e, q in spans],
            "traceable": True,
        })
    return points


def _constraint(text: str) -> list[dict]:
    """抽取约束条件。识别到的写原文，没识别到的明说「未提取到」。"""
    found = []
    pats = [
        (r"不上公有云", "数据不上公有云"),
        (r"暂时不上[^，。；]*", "暂不上云"),
        (r"数据都在[^，。；]*", "数据驻留"),
        (r"必须是[^，。；]*", "强制要求"),
        (r"不能[^，。；]*", "禁止项"),
    ]
    for p, desc in pats:
        m = re.search(p, text)
        if m:
            found.append({"type": desc, "quote": m.group(0), "start": m.start()})
    return found


def build(request: dict) -> dict:
    """从一条原始诉求生成需求说明书数据结构。"""
    for k in ("id", "raw_text"):
        if k not in request:
            raise RequirementError("原始需求缺少字段 %s" % k)
    text = request["raw_text"]
    if not text.strip():
        raise RequirementError("需求 %s 原文为空" % request["id"])

    points = classify(text)
    if not points:
        raise RequirementError(
            "需求 %s 未识别出任何需求点 —— 拒绝生成空壳说明书。"
            "请检查原文是否使用了 A-01 登记的表述方式" % request["id"])

    constraints = _constraint(text)
    spec = {
        "id": request["id"],
        "customer_industry": (request.get("industry") or "").strip() or PENDING,
        "scenario": text,
        "requirement_points": points,
        "constraints": constraints,
        "data_residency": (constraints[0]["type"] if constraints
                            else NOT_FOUND),
        "priority": PENDING,
        "expected_metrics": NOT_FOUND,
        "source": {
            "channel": request.get("channel", "未标注"),
            "received_at": request.get("received_at", "未标注"),
            "reporter": request.get("reporter", "未标注"),
        },
    }
    spec["_quality"] = _completeness(spec)
    spec["_note"] = (
        "「期望指标」保持为「%s」—— **需求原文未给出可量化指标时不编数字**，"
        "由产品经理与客户在需求澄清会上补齐。" % NOT_FOUND)
    return spec


def _completeness(spec: dict) -> dict:
    filled, missing = 0, []
    for f in REQUIRED_FIELDS:
        v = spec.get(f)
        if f == "requirement_points":
            ok = bool(v)
        else:
            ok = bool(v) and v not in (PENDING, NOT_FOUND, "")
        if ok:
            filled += 1
        else:
            missing.append(f)
    total = len(REQUIRED_FIELDS)
    return {
        "required_total": total,
        "required_filled": filled,
        "missing_fields": missing,
        "completeness": round(filled / total, 4),
        "note": ("完整率是**需求澄清进度**的可测量指标，不是文档质量指标。"
                 "需求刚收集时必然不完整 —— 需要在澄清会上补齐。"),
    }


def field_rows(spec: dict) -> list[list]:
    """转成表格行，供文档渲染用。"""
    rows = []
    for f in REQUIRED_FIELDS + ["data_residency"]:
        v = spec.get(f)
        if f == "requirement_points":
            v = "；".join("%s %s" % (p["id"], p["label_cn"]) for p in v) if v else ""
        elif f == "constraints":
            v = "；".join(c["type"] for c in v) if v else "未提取到"
        rows.append([FIELD_LABEL[f], v if v else "未填"])
    return rows
