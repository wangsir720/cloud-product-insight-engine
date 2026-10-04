# -*- coding: utf-8 -*-
"""competitor_matrix / prototype_helper / report_builder 测试。

核心验证点：**不做优劣评分**、**空白项如实呈现**、**流程图由代码生成**。
"""
import os

import pytest

from src.catalog import LAYERS, VENDOR_LABEL, load_products, load_requests
from src.competitor_matrix import CompetitorError, build_matrix, category_map
from src.prototype_helper import (PrototypeError, architecture_flow, count_nodes,
                                  render_mermaid, requirement_flow)
from src.report_builder import build as build_report
from src.requirement_builder import build as build_spec


# ---------------- 竞品矩阵 ----------------

def test_matrix_covers_five_layers():
    """五层是行业通行的云服务分层口径。"""
    d = build_matrix()
    assert d["layers"] == LAYERS
    assert len(d["layers"]) == 5
    for l in d["layers"]:
        assert l in d["matrix"][d["vendors"][0]]


def test_all_four_vendors_present():
    d = build_matrix()
    assert set(d["vendors"]) == {"Sugon", "HuaweiCloud", "Aliyun", "TencentCloud"}
    for v in d["vendors"]:
        assert VENDOR_LABEL.get(v), "%s 缺中文名" % v


def test_every_product_has_citation():
    d = build_matrix()
    for v in d["vendors"]:
        for l in d["layers"]:
            for p in d["matrix"][v][l]["products"]:
                assert "来源" in p["cite"] and "可信度" in p["cite"]


def test_gaps_are_reported_not_filled():
    """核心纪律：某厂商某层未查到就报空白，不推测填充。"""
    d = build_matrix()
    assert d["gap_count"] > 0, "应存在空白项（个别厂商的 SaaS 层等）"
    for g in d["gaps"]:
        assert g["status"] == "未查到"
        assert "不做推测填充" in g["note"]


def test_placeholder_rows_not_counted_as_coverage():
    """「未查到」占位行不得计入覆盖度。"""
    d = build_matrix()
    # 该厂商的 SaaS 行产品名为「未查到」，应计入空白而非覆盖
    sugon_saas = d["matrix"]["Sugon"]["SaaS"]
    assert sugon_saas["count"] == 0, "占位行不得计入产品数"
    assert any(g["vendor"] == "Sugon" and g["layer"] == "SaaS"
               for g in d["gaps"]), "该厂商的 SaaS 应出现在空白项里"


def test_coverage_rates_bounded():
    d = build_matrix()
    c = d["coverage"]
    for k in ("vendor_rate", "layer_rate", "category_rate"):
        assert 0 <= c[k] <= 1, "%s 应在 0-1 之间" % k


def _matrix_data_only(d: dict) -> str:
    """只取数据部分，排除 discipline 声明文本。

    纪律声明本身必然含「不做优劣评分」这类词，用它做关键词扫描会误判。
    """
    import json
    payload = {k: v for k, v in d.items() if k != "discipline"}
    return json.dumps(payload, ensure_ascii=False, default=str)


def test_no_ranking_or_scoring():
    """核心纪律：只做产品线认知层面对标，不评判谁更强。

    只查**数据字段**——纪律声明里必然出现「不做优劣评分」这些词。
    """
    raw = _matrix_data_only(build_matrix())
    for banned in ("score", "rank", "rating", "评分", "排名", "推荐序", "优于"):
        assert banned not in raw, "矩阵数据不应含 %s" % banned


def test_no_price_or_sla():
    raw = _matrix_data_only(build_matrix()).lower()
    for banned in ("price", "sla_", "价格", "元/核", "折扣"):
        assert banned not in raw, "不应收录 %s" % banned


def test_category_map_consistent():
    d = build_matrix()
    cmap = category_map(d)
    assert cmap
    for row in cmap:
        assert set(row["vendors"]) == set(d["vendors"])
        assert any(row["vendors"].values()), "%s 至少被一家覆盖" % row["category"]


def test_matrix_requires_data(monkeypatch):
    import src.competitor_matrix as cm
    monkeypatch.setattr(cm, "load_products", lambda: [])
    with pytest.raises(CompetitorError):
        build_matrix()


# ---------------- 流程图（替代 Axure/XMind） ----------------

def test_requirement_flow_is_mermaid():
    s = build_spec(load_requests()[0])
    flow = requirement_flow(s)
    assert flow.startswith("flowchart TD")
    st = count_nodes(flow)
    assert st["nodes"] >= 5 and st["edges"] >= 5
    assert st["is_mermaid"]


def test_flow_includes_clarification_loop():
    """需求澄清会与「需补充」回流是产品流程的关键闭环。"""
    s = build_spec(load_requests()[0])
    flow = requirement_flow(s)
    assert "需求澄清会" in flow
    assert "需补充" in flow, "必须有澄清后回流的路径"
    assert "技术交流材料" in flow, "须覆盖技术交流与投标支持"


def test_architecture_flow_covers_layers():
    d = build_matrix()
    flow = architecture_flow(d)
    assert flow.startswith("flowchart LR")
    for l in d["layers"]:
        assert l.upper() in flow


def test_render_mermaid_rejects_invalid():
    with pytest.raises(PrototypeError):
        render_mermaid("这不是流程图")


def test_flow_requires_points():
    with pytest.raises(PrototypeError):
        requirement_flow({"requirement_points": []})


# ---------------- 周月报 ----------------

def test_report_kpis_computed():
    specs = [build_spec(r) for r in load_requests()]
    d = build_matrix()
    r = build_report(specs, d, "周报")
    names = {k["name"] for k in r["kpi"]}
    for n in ("需求数", "需求点总数", "平均字段完整率", "竞品空白项"):
        assert n in names


def test_report_excludes_business_forecasts():
    """无业务数据，绝不做营收或用户增长预测。"""
    specs = [build_spec(r) for r in load_requests()]
    r = build_report(specs, build_matrix())
    joined = "".join(r["exclusions"])
    assert "不做营收预测" in joined, "必须显式声明不做营收预测"
    assert "不做用户增长预测" in joined, "必须显式声明不做用户增长预测"
    assert "占位值" in joined, "占位参数须声明为占位"


def test_report_rejects_empty_requirements():
    with pytest.raises(ValueError):
        build_report([], build_matrix())


def test_requirement_distribution_sums_to_total():
    specs = [build_spec(r) for r in load_requests()]
    r = build_report(specs, build_matrix())
    total = r["kpi"][1]["value"]
    assert sum(d["count"] for d in r["requirement_distribution"]) == total
    shares = sum(d["share"] for d in r["requirement_distribution"])
    assert shares == pytest.approx(1.0, rel=1e-6)
