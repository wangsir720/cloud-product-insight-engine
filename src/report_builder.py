#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""周/月度数据分析报告生成。

把产品数据监控与周/月分析报告从手工整理变成可复算的脚本。

## 为什么用脚本而不是 Excel/BI

Excel/BI 工具解决的是「**数据已经结构化好**」之后的分析。
但产品经理真正的瓶颈在前一步：**需求信息本身没有结构**。

本工具的价值在于：把「需求管道自身的健康度」变成可测量指标，
并直接输出报告草稿 —— **数据源就是本项目的需求数据，不是另接一个 BI 系统**。

## 覆盖的指标（C-01 登记）

| 指标 | 说明 |
|---|---|
| 需求数 | 期内条目数 |
| 类型分布 | 各需求点类型占比 |
| 字段完整率 | 需求澄清进度 |
| 竞品对标覆盖度 | 厂商/层/能力域覆盖率 |
| **空白项数** | 未查到公开产品的格子数 |

**不做业务营收预测、不做用户增长预测** —— 本项目没有业务数据，
任何预测数字都只能是编的。
"""
from __future__ import annotations

import datetime

from .requirement_builder import REQUIREMENT_LABEL


def build(requirements: list[dict], competitor: dict, period: str = "周报") -> dict:
    """生成周/月报数据结构。"""
    if not requirements:
        raise ValueError("需求集为空，无法生成报告 —— 空报告没有决策价值")

    total_points = 0
    by_label = {}
    for spec in requirements:
        for p in spec.get("requirement_points", []):
            total_points += 1
            by_label[p["label"]] = by_label.get(p["label"], 0) + 1

    comps = [s["_quality"]["completeness"] for s in requirements]
    missing_counter = {}
    for s in requirements:
        for f in s["_quality"]["missing_fields"]:
            missing_counter[f] = missing_counter.get(f, 0) + 1

    cov = competitor["coverage"]
    now = datetime.datetime.now().strftime("%Y-%m-%d")

    return {
        "period": period,
        "generated_at": now,
        "kpi": [
            {"name": "需求数", "value": len(requirements), "unit": "条",
             "definition": "期内收集的客户需求条目数"},
            {"name": "需求点总数", "value": total_points, "unit": "个",
             "definition": "按 A-01 规则从原始诉求拆出的需求点数量"},
            {"name": "平均字段完整率", "value": round(sum(comps) / len(comps), 4),
             "unit": "", "definition": "已填必填字段数 ÷ 必填字段总数",
             "note": "这是**需求澄清进度**，不是文档质量"},
            {"name": "竞品厂商覆盖率", "value": cov["vendor_rate"], "unit": "",
             "definition": "有产品条目的厂商数 ÷ 厂商总数"},
            {"name": "竞品层覆盖率", "value": cov["layer_rate"], "unit": "",
             "definition": "有产品条目的层数 ÷ 5 层"},
            {"name": "能力域覆盖率", "value": cov["category_rate"], "unit": "",
             "definition": "有产品条目的能力域数 ÷ 全部能力域数"},
            {"name": "竞品空白项", "value": competitor["gap_count"], "unit": "格",
             "definition": "某厂商在某层未查到公开产品的格子数",
             "note": "空白项是信息，不是缺陷"},
        ],
        "requirement_distribution": [
            {"label": REQUIREMENT_LABEL.get(k, k), "key": k, "count": v,
             "share": round(v / total_points, 4) if total_points else 0.0}
            for k, v in sorted(by_label.items(), key=lambda x: -x[1])
        ],
        "pending_fields": [
            {"field": f, "count": c,
             "note": "该字段在 %d 条需求中待补充，**须在需求澄清会上补齐**" % c}
            for f, c in sorted(missing_counter.items(), key=lambda x: -x[1])
        ],
        "competitor_snapshot": {
            "vendors": competitor["vendors"],
            "product_count": competitor["product_count"],
            "gap_count": competitor["gap_count"],
        },
        "exclusions": [
            "无业务营收数据，**不做营收预测**",
            "无用户行为数据，**不做用户增长预测**",
            "平均澄清轮次需真实工单记录，当前为占位值",
        ],
    }
