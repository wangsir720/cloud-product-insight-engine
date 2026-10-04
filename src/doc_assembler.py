# -*- coding: utf-8 -*-
"""文档装配：需求说明书 / 竞品分析报告 / 技术交流材料 / 周月报。

覆盖需求说明书、使用手册、竞品分析报告、周/月分析报告，
以及支持售前技术交流与投标的交付材料。

用标准库字符串模板而非模板引擎 —— 保持零第三方依赖是本项目的一贯取舍。
"""
from __future__ import annotations

import csv
import json
import os

from .catalog import CATEGORY_LABEL, LAYER_LABEL, VENDOR_LABEL
from .requirement_builder import FIELD_LABEL, PENDING
from .prototype_helper import architecture_flow, render_mermaid, requirement_flow


def _table(headers, rows) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join("" if c is None else str(c) for c in r) + " |")
    return "\n".join(out)


def render_prd(spec: dict) -> str:
    """需求说明书。"""
    L = ["# 需求说明书 · %s" % spec["id"], ""]
    L.append("> 由 `src/doc_assembler.py` 自动装配。"
             "**客户场景为自拟，非真实业务数据。**")
    L.append("")
    L.append("## 1. 需求信息")
    L.append(_table(
        ["字段", "值"],
        [["来源渠道", spec["source"]["channel"]],
         ["接收日期", spec["source"]["received_at"]],
         ["上报人", spec["source"]["reporter"]],
         ["客户行业", spec["customer_industry"]]]))
    L.append("")
    L.append("## 2. 业务场景描述")
    L.append("")
    L.append("> %s" % spec["scenario"])
    L.append("")
    L.append("## 3. 需求点清单（每个可追溯到原文）")
    L.append("")
    L.append(_table(["编号", "类型", "原文依据"],
                    [[p["id"], p["label_cn"],
                      "；".join("「%s」" % e["quote"] for e in p["evidence"])]
                     for p in spec["requirement_points"]]))
    L.append("")
    L.append("## 4. 约束条件")
    L.append("")
    if spec["constraints"]:
        L.append(_table(["类型", "原文"],
                        [[c["type"], "「%s」" % c["quote"]] for c in spec["constraints"]]))
    else:
        L.append("**未提取到明确约束条件** —— 需在需求澄清会上确认。")
    L.append("")
    L.append("## 5. 字段完整度")
    L.append("")
    q = spec["_quality"]
    L.append("**必填字段完整率 %.0f%%**（%d/%d）"
             % (q["completeness"] * 100, q["required_filled"], q["required_total"]))
    L.append("")
    if q["missing_fields"]:
        L.append("**待补充字段**：%s"
                 % "、".join(FIELD_LABEL[f] for f in q["missing_fields"]))
    L.append("")
    L.append("> %s" % q["note"])
    L.append("")
    L.append("> %s" % spec["_note"])
    L.append("")
    L.append("## 6. 需求流转流程图")
    L.append("")
    L.append(render_mermaid(requirement_flow(spec)))
    L.append("")
    L.append("> 流程图由代码生成（`src/prototype_helper.py`），"
             "纯文本可版本 diff —— 需求变更时能直接看到改了什么，"
             "这是手工画图做不到的。")
    L.append("")
    L.append("## 7. 待明确事项")
    L.append("")
    for i, item in enumerate([
        "期望指标：需求原文未给出可量化指标，**不编数字**，须在澄清会上与客户共同定义",
        "优先级：须结合客户业务窗口期确定",
        "数据驻留要求的具体范围（哪些数据必须留在机房、哪些可上云）",
        "竞品对标的业务口径：客户想对标的是能力还是价格",
    ], 1):
        L.append("%d. %s" % (i, item))
    L.append("")
    L.append("---")
    L.append("生成命令：`python -m src.cli`")
    L.append("")
    return "\n".join(L)


def render_competitor_report(data: dict) -> str:
    """竞品分析报告。"""
    L = ["# 云计算产品竞品对标报告", ""]
    L.append("> 由 `src/doc_assembler.py` 自动装配。"
             "**客户场景为自拟、非真实业务数据；产品数据为各厂商公开产品资料，"
             "非私有制产品的内部能力。**")
    L.append("")
    L.append("> %s" % data["discipline"].replace("\n", "  \n> "))
    L.append("")

    L.append("## 1. 覆盖度总览")
    cov = data["coverage"]
    L.append(_table(["指标", "值", "口径"], [
        ["产品条目数", data["product_count"], "有效产品行数（不含「未查到」占位）"],
        ["厂商覆盖率", "%.0f%%（%d/%d）" % (cov["vendor_rate"] * 100,
                                          cov["vendor_covered"], cov["vendor_total"]),
         "有产品条目的厂商占比"],
        ["层覆盖率", "%.0f%%（%d/%d）" % (cov["layer_rate"] * 100,
                                        cov["layer_covered"], cov["layer_total"]),
         "有产品条目的云产品层数占比（五层口径）"],
        ["能力域覆盖率", "%.0f%%（%d/%d）" % (cov["category_rate"] * 100,
                                           cov["category_covered"], cov["category_total"]),
         "有产品条目的能力域占比"],
        ["**空白项**", "**%d 格**" % data["gap_count"],
         "某厂商在某层未查到公开产品 —— **这是信息，不是缺陷**"],
    ]))
    L.append("")

    L.append("## 2. 五层产品对标矩阵")
    L.append("")
    layers = data["layers"]
    matrix_rows = []
    for l in layers:
        cells = [LAYER_LABEL[l]]
        for v in data["vendors"]:
            cell = data["matrix"][v][l]
            if cell["count"] == 0:
                cells.append("**未查到**")
            else:
                names = "、".join(p["name"] for p in cell["products"])
                cells.append("%d 个：%s" % (cell["count"], names))
        matrix_rows.append(cells)
    L.append(_table(["云产品层"] + [VENDOR_LABEL.get(v, v) for v in data["vendors"]],
                    matrix_rows))
    L.append("")
    L.append("> **五层是行业通行的云服务分层口径**（IaaS/PaaS/DAAS/MASS/SaaS），"
             "不是本项目的自创分类。")
    L.append("")

    L.append("### 2.1 能力域横向对照")
    L.append("")
    from .competitor_matrix import category_map
    cmap = category_map(data)
    L.append(_table(["能力域"] + [VENDOR_LABEL.get(v, v) for v in data["vendors"]],
                    [[CATEGORY_LABEL.get(r["category"], r["category"])]
                     + ["✓" if r["vendors"][v] else "—" for v in data["vendors"]]
                     for r in cmap]))
    L.append("")
    L.append("> ✓ = 有公开产品条目；— = 未查到。**空格不代表能力缺失，只代表公开资料里没有。**")
    L.append("")

    L.append("### 2.2 能力域结构图")
    L.append("")
    L.append(render_mermaid(architecture_flow(data)))
    L.append("")

    L.append("## 3. 空白项清单")
    L.append("")
    if data["gaps"]:
        L.append(_table(["厂商", "云产品层", "状态"],
                        [[g["vendor_label"], g["layer_label"], g["status"]]
                         for g in data["gaps"]]))
        L.append("")
        L.append("> 空白项的使用方式：**在技术交流时明确告知客户该层我们暂无可查的公开信息**，"
                 "而不是含糊带过或编一个。**诚信本身是产品经理的竞争力。**")
    else:
        L.append("无空白项 —— 五层均有产品条目。")
    L.append("")

    L.append("## 4. 本报告未做的事")
    for line in [
        "**不做优劣评分、不排名、不给推荐序**：只做产品线认知层面对标，不做评判",
        "**不收录价格与 SLA 数字**：属商业条款，无稳定公开口径",
        "**不推测未公开的能力**：查不到就是查不到",
        "**不做营收或市场份额预测**：无数据",
    ]:
        L.append("- %s" % line)
    L.append("")
    L.append("---")
    L.append("生成命令：`python -m src.cli`")
    L.append("")
    return "\n".join(L)


def render_tech_talk(spec: dict, data: dict) -> str:
    """技术交流材料（支持售前技术交流与投标）。"""
    L = ["# 技术交流材料 · %s" % spec["customer_industry"], ""]
    L.append("> 由 `src/doc_assembler.py` 自动装配。"
             "**客户场景为自拟，打单价格与商务条款不在本材料范围内。**")
    L.append("")
    L.append("## 1. 客户当前状况")
    L.append("")
    L.append("%s" % spec["scenario"])
    L.append("")
    L.append("## 2. 客户诉求与我们的对应能力")
    L.append("")
    L.append(_table(["客户诉求", "对应云产品层", "我方能力域覆盖"],
                    [[p["label_cn"],
                      {"migration": "IaaS", "ops_efficiency": "PaaS",
                       "scheduling": "PaaS / MASS", "competitor": "—",
                       "compliance": "MASS（私有化）", "cost": "—",
                       "performance": "IaaS / MASS", "sla": "IaaS / PaaS"}
                       .get(p["label"], "—"),
                      "、".join(sorted({
                          c for v in data["vendors"]
                          for l in data["layers"]
                          for c in data["matrix"][v][l]["categories"]
                      })[:3]) or "—"]
                     for p in spec["requirement_points"]]))
    L.append("")
    L.append("## 3. 竞品对标要点")
    L.append("")
    L.append("| 云产品层 | 我方 | 华为云 | 阿里云 | 腾讯云 |")
    L.append("|---|---|---|---|---|")
    for l in data["layers"]:
        cells = []
        for v in data["vendors"]:
            n = data["matrix"][v][l]["count"]
            cells.append("%d 个" % n if n else "未查到")
        L.append("| %s | %s |" % (LAYER_LABEL[l], " | ".join(cells)))
    L.append("")
    L.append("> 对标口径：只讲各厂商**在公开产品页上能查到的产品线**，"
             "不做优劣评价。客户结合自身场景判断，比我们替他判断更负责。")
    L.append("")
    L.append("## 4. 实施路径")
    L.append("")
    L.append(render_mermaid(requirement_flow(spec)))
    L.append("")
    L.append("## 5. 待与客户确认")
    L.append("")
    for i, item in enumerate([
        "期望指标：性能与成本的具体目标值（**本材料不代客户设定**）",
        "优先级与时间窗口",
        "数据驻留的具体范围",
        "预算与采购流程",
    ], 1):
        L.append("%d. %s" % (i, item))
    L.append("")
    L.append("---")
    L.append("生成命令：`python -m src.cli`")
    L.append("")
    return "\n".join(L)


def render_report(r: dict) -> str:
    """周/月度数据分析报告。"""
    L = ["# %s · 数据分析报告" % r["period"], ""]
    L.append("> 由 `src/doc_assembler.py` 生成，生成于 %s。"
             "**客户场景为自拟、非真实业务数据；数据源为本项目的需求管道，"
             "非业务营收数据。**" % r["generated_at"])
    L.append("")
    L.append("## 1. 核心指标")
    L.append(_table(["指标", "值", "定义", "备注"],
                    [[k["name"], k["value"], k["definition"], k.get("note", "—")]
                     for k in r["kpi"]]))
    L.append("")
    L.append("## 2. 需求类型分布")
    L.append("")
    L.append(_table(["需求类型", "数量", "占比"],
                    [[d["label"], d["count"], "%.0f%%" % (d["share"] * 100)]
                     for d in r["requirement_distribution"]]))
    L.append("")
    L.append("## 3. 待补充字段（需求澄清进度）")
    L.append("")
    if r["pending_fields"]:
        L.append(_table(["字段", "待补充条数", "说明"],
                        [[p["field"], p["count"], p["note"]]
                         for p in r["pending_fields"]]))
    else:
        L.append("无待补充字段。")
    L.append("")
    L.append("## 4. 竞品对标快照")
    L.append("")
    snap = r["competitor_snapshot"]
    L.append(_table(["项", "值"], [
        ["覆盖厂商", "、".join(VENDOR_LABEL.get(v, v) for v in snap["vendors"])],
        ["产品条目数", snap["product_count"]],
        ["空白项", "%d 格" % snap["gap_count"]],
    ]))
    L.append("")
    L.append("## 5. 本报告未覆盖的内容")
    for line in r["exclusions"]:
        L.append("- %s" % line)
    L.append("")
    L.append("---")
    L.append("生成命令：`python -m src.cli`")
    L.append("")
    return "\n".join(L)


def save(text: str, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def save_csv(rows, header, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def save_json(obj, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
    return path
