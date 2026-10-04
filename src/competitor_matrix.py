# -*- coding: utf-8 -*-
"""竞品对标矩阵生成。

对标主流云计算厂商的公开产品线（IaaS/PaaS/DAAS/MASS/SaaS 五层）：
只并列客观信息、不做优劣评分。

## 这个模块的核心判断

这个工具做的是「**对产品线的认知**」，不是「你会不会做竞品分析报告」。

这个区别决定了工具的形态：

| 应该做 | 不应该做 |
|---|---|
| 并列各厂商在五层云产品上的**客观产品线** | 打分、排名、推荐序 |
| 每条注明**来源与抓取日期** | 收录价格与 SLA（商业条款） |
| 显式列出**对方没查到的东西** | 推测对方未公开的能力 |

**「空白项」是这个工具的一半价值。** 竞品对标不只是知道对方有什么，
同样是知道对方没什么 —— 以及自己有什么是对方没有的。
"""
from __future__ import annotations

from .catalog import (CATEGORY_LABEL, LAYER_LABEL, LAYERS, NOT_FOUND,
                      VENDOR_LABEL, load_products, vendors)


class CompetitorError(Exception):
    pass


def build_matrix() -> dict:
    """生成五层云产品 × 四厂商的对标矩阵。"""
    rows = load_products()
    if not rows:
        raise CompetitorError("产品矩阵为空")

    vs = vendors()
    # 只统计有效产品条目（「未查到」占位行不算覆盖）
    valid = [r for r in rows if r.found]
    if not valid:
        raise CompetitorError("产品矩阵中无有效产品条目")

    matrix = {}
    for v in vs:
        vrows = [r for r in valid if r.vendor == v]
        by_layer = {}
        for layer in LAYERS:
            items = [r for r in vrows if r.layer == layer]
            by_layer[layer] = {
                "vendor": v,
                "vendor_label": VENDOR_LABEL.get(v, v),
                "layer": layer,
                "layer_label": LAYER_LABEL[layer],
                "products": [
                    {"name": r.key,
                     "category": r.category,
                     "category_label": CATEGORY_LABEL.get(r.category, r.category or NOT_FOUND),
                     "positioning": r.s("positioning") or NOT_FOUND,
                     "cite": r.cite()}
                    for r in items],
                "count": len(items),
                "categories": sorted({r.category for r in items if r.category}),
            }
        matrix[v] = by_layer

    # 覆盖度统计
    vendor_cov = [v for v in vs if sum(
        matrix[v][l]["count"] for l in LAYERS) > 0]
    layer_cov = [l for l in LAYERS if sum(
        matrix[v][l]["count"] for v in vs) > 0]
    all_categories = sorted({r.category for r in valid if r.category})
    cat_cov = [c for c in all_categories if any(
        r.category == c for r in valid)]

    # 空白项：某厂商在某层未查到公开产品
    gaps = []
    for v in vs:
        for l in LAYERS:
            if matrix[v][l]["count"] == 0:
                gaps.append({
                    "vendor": v, "vendor_label": VENDOR_LABEL.get(v, v),
                    "layer": l, "layer_label": LAYER_LABEL[l],
                    "status": NOT_FOUND,
                    "note": "%s 在 %s 层**未查到公开产品条目** —— "
                            "这是真实的信息缺口，不做推测填充"
                            % (VENDOR_LABEL.get(v, v), LAYER_LABEL[l]),
                })

    return {
        "vendors": vs,
        "layers": LAYERS,
        "matrix": matrix,
        "product_count": len(valid),
        "coverage": {
            "vendor_total": len(vs),
            "vendor_covered": len(vendor_cov),
            "vendor_rate": round(len(vendor_cov) / len(vs), 4) if vs else 0.0,
            "layer_total": len(LAYERS),
            "layer_covered": len(layer_cov),
            "layer_rate": round(len(layer_cov) / len(LAYERS), 4),
            "category_total": len(all_categories),
            "category_covered": len(cat_cov),
            "category_rate": round(len(cat_cov) / len(all_categories), 4)
            if all_categories else 0.0,
        },
        "gaps": gaps,
        "gap_count": len(gaps),
        "discipline": (
            "**只录公开信息、每条注明来源与日期、不做优劣评分。**\n"
            "本矩阵只做产品线认知层面对标，不评判谁更强 —— "
            "所以本矩阵不排名、不打分、不收录价格与 SLA。\n"
            "空白项是输出的一部分：知道对方没什么，与知道对方有什么同样重要。"),
        "assumption_refs": ["B-01", "B-02", "B-03"],
    }


def category_map(data: dict) -> list[dict]:
    """按能力域横向对照：各家覆盖了哪些能力域。"""
    vs = data["vendors"]
    cats = sorted({cat for v in vs for l in LAYERS
                   for cat in data["matrix"][v][l]["categories"]})
    rows = []
    for cat in cats:
        rows.append({
            "category": cat,
            "category_label": CATEGORY_LABEL.get(cat, cat),
            "vendors": {
                v: any(cat in data["matrix"][v][l]["categories"] for l in LAYERS)
                for v in vs
            },
        })
    return rows
