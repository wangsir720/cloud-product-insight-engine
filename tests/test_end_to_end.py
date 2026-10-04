# -*- coding: utf-8 -*-
"""端到端测试：产物完整性、声明、无贬低表述、敏感信息。"""
import json
import os

from src import cli

ARTIFACTS = ["prd_draft.md", "competitor_report.md", "tech_talk.md",
             "weekly_report.md", "competitor_matrix.csv", "result.json"]


def _doc(name):
    with open(os.path.join(cli.OUTPUT_DIR, name), encoding="utf-8") as f:
        return f.read()


def test_all_artifacts_generated():
    assert cli.main([]) == 0
    for name in ARTIFACTS:
        p = os.path.join(cli.OUTPUT_DIR, name)
        assert os.path.isfile(p), "缺少产物 %s" % name
        assert os.path.getsize(p) > 0, "产物为空 %s" % name


def test_prd_has_required_sections():
    assert cli.main([]) == 0
    doc = _doc("prd_draft.md")
    for h in ("## 1. 需求信息", "## 2. 业务场景描述", "## 3. 需求点清单",
              "## 4. 约束条件", "## 5. 字段完整度", "## 6. 需求流转流程图",
              "## 7. 待明确事项"):
        assert h in doc, "需求说明书缺少章节：%s" % h


def test_prd_points_have_evidence_table():
    assert cli.main([]) == 0
    doc = _doc("prd_draft.md")
    assert "原文依据" in doc
    assert "需求点清单（每个可追溯到原文）" in doc


def test_prd_declares_metrics_not_fabricated():
    assert cli.main([]) == 0
    doc = _doc("prd_draft.md")
    assert "不编数字" in doc or "未提取到" in doc
    assert "待补充" in doc


def test_competitor_report_covers_five_layers():
    assert cli.main([]) == 0
    doc = _doc("competitor_report.md")
    for l in ("基础设施即服务", "平台即服务", "数据即服务",
              "异构算力即服务", "软件即服务"):
        assert l in doc, "缺少云产品层 %s" % l


def test_competitor_report_has_no_demotion():
    """贬低词扫描须排除纪律声明段（声明里会出现「不做优劣评价」）。"""
    doc = _doc("competitor_report.md")
    body = doc.split("## 1. 覆盖度总览", 1)[-1]
    for banned in ("优于", "领先于", "吊打", "远超", "不如", "落后于", "碾压"):
        assert banned not in body, "出现贬低性表述：%s" % banned


def test_competitor_report_declares_gaps():
    doc = _doc("competitor_report.md")
    assert "空白项" in doc
    assert "不是缺陷" in doc or "是信息" in doc


def test_tech_talk_supports_bidding():
    """JD 职责 6：支持售前及销售，完成技术交流、打单。"""
    assert cli.main([]) == 0
    doc = _doc("tech_talk.md")
    assert "技术交流材料" in doc
    assert "待与客户确认" in doc
    assert "不对标" in doc or "对标口径" in doc


def test_flow_is_code_generated_not_axure():
    for name in ("prd_draft.md", "tech_talk.md", "competitor_report.md"):
        doc = _doc(name)
        assert "```mermaid" in doc, "%s 应含代码生成的流程图" % name
    assert "可版本 diff" in _doc("prd_draft.md")


def test_weekly_report_has_kpis():
    assert cli.main([]) == 0
    doc = _doc("weekly_report.md")
    assert "核心指标" in doc
    assert "需求类型分布" in doc
    assert "本报告未覆盖的内容" in doc


def test_competitor_only_mode():
    assert cli.main(["--competitor"]) == 0
    assert os.path.isfile(os.path.join(cli.OUTPUT_DIR, "competitor_report.md"))


def test_reports_declare_synthetic_scenario():
    assert cli.main([]) == 0
    for name in ("prd_draft.md", "competitor_report.md", "tech_talk.md",
                 "weekly_report.md"):
        doc = _doc(name)
        assert "自拟" in doc, "%s 缺自拟声明" % name


def test_no_sensitive_fields():
    assert cli.main([]) == 0
    banned = ["合同金额", "客户名称", "内部报价", "账号密码", "有限公司"]
    for name in ("prd_draft.md", "competitor_report.md", "tech_talk.md",
                 "weekly_report.md"):
        doc = _doc(name)
        for b in banned:
            assert b not in doc, "%s 出现 %s" % (name, b)


def test_generation_is_reproducible():
    cli.main([])
    with open(os.path.join(cli.OUTPUT_DIR, "result.json"), encoding="utf-8") as f:
        a = json.load(f)
    cli.main([])
    with open(os.path.join(cli.OUTPUT_DIR, "result.json"), encoding="utf-8") as f:
        b = json.load(f)
    assert a["competitor"] == b["competitor"]
    assert a["requirements"] == b["requirements"]


def test_every_csv_row_has_source():
    import csv
    assert cli.main([]) == 0
    with open(os.path.join(cli.OUTPUT_DIR, "competitor_matrix.csv"),
              encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert rows
    for r in rows:
        if r["产品名"] != "未查到":
            assert "来源" in r["来源"], "产品 %s 缺来源" % r["产品名"]
