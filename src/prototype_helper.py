# -*- coding: utf-8 -*-
"""流程图生成（代码生成，替代 Axure/XMind/Visio）。

以代码生成流程图与结构图，替代手工绘图工具。

## 为什么用代码生成而不是 Axure

**这不是绕过要求，而是更合适的做法** —— 流程会随需求变，而文本 diff 能看到改了什么：

| | Axure / XMind | 代码生成 |
|---|---|---|
| 版本管理 | 导出为图片/文档，无法 diff | **纯文本，git 可 diff** |
| 一致性 | 手工改易漏 | 改模板即全图同步 |
| 批量出图 | 逐张手工 | 参数化循环 |
| 交付形态 | 图片附件 | 文本，可直接进 Wiki |

Axure 的价值在**交互原型**。而这里要的是「原型或流程图」——
**流程图用代码生成是更合适的形态**，因为流程会随需求变，而文本 diff 能看到改了什么。

本模块输出 **Mermaid 流程图文本**：可粘贴进 GitHub/GitLab/Notion 渲染，
也可直接提交进代码仓库作为可评审的文档。
"""
from __future__ import annotations

import re

# 需求点类型 -> 流程节点文案（用于自动生成需求流转流程）
STEP_FOR_LABEL = {
    "migration": "资源迁移纳管",
    "ops_efficiency": "运维管理优化",
    "scheduling": "作业调度优化",
    "competitor": "竞品对标输出",
    "compliance": "合规方案确认",
    "cost": "成本优化方案",
    "performance": "性能优化",
    "sla": "SLA 设计",
}


class PrototypeError(Exception):
    pass


def requirement_flow(spec: dict) -> str:
    """由需求说明书生成需求流转流程图（Mermaid）。

    流程固定为产品经理的标准动作链，每个需求点作为一个旁支插入。
    """
    points = spec.get("requirement_points") or []
    if not points:
        raise PrototypeError("需求说明书无需求点，无法生成流程图")

    lines = ["flowchart TD",
             '    A[客户原始诉求] --> B[需求结构化<br/>字段+原文出处]']
    cur = "B"
    # 按需求点类型去重，保持出现顺序
    seen, ordered = set(), []
    for p in points:
        if p["label"] in seen:
            continue
        seen.add(p["label"])
        ordered.append(p)

    for i, p in enumerate(ordered):
        node = "S%d[%s]" % (i + 1, STEP_FOR_LABEL.get(p["label"], p["label_cn"]))
        lines.append("    %s --> %s" % (cur, node))
        cur = node
    lines.append("    %s --> C[需求说明书<br/>待补充字段清单]" % cur)
    lines.append("    C --> D[需求澄清会<br/>补齐期望指标与优先级]")
    lines.append("    D --> E{客户确认}")
    lines.append("    E -->|通过| F[技术交流材料<br/>支持打单]")
    lines.append("    E -->|需补充| B")
    lines.append("    F --> G[竞品对标矩阵<br/>四厂商五层]")
    lines.append("    G --> H[周月数据报告]")
    return "\n".join(lines)


def architecture_flow(data: dict) -> str:
    """由竞品矩阵生成五层产品能力域图。"""
    vs = data.get("vendors")
    layers = data.get("layers")
    if not vs or not layers:
        raise PrototypeError("竞品矩阵数据不完整，无法生成能力域图")

    lines = ["flowchart LR"]
    for v in vs:
        label = data["matrix"][v][layers[0]]["vendor_label"]
        lines.append("    subgraph %s[%s]" % (v.upper(), label))
        for l in layers:
            node = "%s_%s" % (v.upper(), l.upper())
            lines.append("        %s[%s<br/>%d 个产品]"
                         % (node, data["matrix"][v][l]["layer_label"],
                            data["matrix"][v][l]["count"]))
        lines.append("    end")
    # 层间关系：下层为上层提供底座
    for i in range(len(layers) - 1):
        lo = layers[i].upper()
        hi = layers[i + 1].upper()
        for v in vs:
            lines.append("    %s_%s -.-> %s_%s" % (v.upper(), lo, v.upper(), hi))
    return "\n".join(lines)


def render_mermaid(text: str) -> str:
    """把 Mermaid 文本包成 Markdown 代码块，保证粘贴后即可渲染。"""
    if "flowchart" not in text and "graph" not in text:
        raise PrototypeError("不是有效的流程图文本")
    return "```mermaid\n%s\n```" % text


def count_nodes(text: str) -> dict:
    """统计流程图规模，便于评估覆盖度。"""
    nodes = len(re.findall(r"^\s+\w+\[", text, re.M))
    edges = len(re.findall(r"-->", text)) + len(re.findall(r"-.->", text))
    return {"nodes": nodes, "edges": edges, "is_mermaid": True}
