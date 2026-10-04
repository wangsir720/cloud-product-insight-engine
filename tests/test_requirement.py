# -*- coding: utf-8 -*-
"""requirement_builder 测试 —— 重点验证「需求点可追溯」与「不编数字」。"""
import pytest

from src.requirement_builder import (NOT_FOUND, PENDING, REQUIRED_FIELDS,
                                     RequirementError, build, classify)


def _req(text, **kw):
    r = {"id": "T-1", "raw_text": text}
    r.update(kw)
    return r


# ---------------- 需求点可追溯 ----------------

def test_every_point_has_evidence():
    s = build(_req("客户说管理麻烦，希望统一管，还问了对标华为云"))
    assert s["requirement_points"]
    for p in s["requirement_points"]:
        assert p["traceable"], "%s 无出处即为编造" % p["id"]
        assert p["evidence"], "%s 缺原文依据" % p["id"]
        for e in p["evidence"]:
            assert e["quote"], "出处必须有原文片段"
            assert e["start"] < e["end"], "出处须有有效字符区间"


def test_evidence_quote_appears_in_raw_text():
    text = "客户说管理麻烦，希望统一管"
    s = build(_req(text))
    for p in s["requirement_points"]:
        for e in p["evidence"]:
            assert e["quote"] in text, "引用的原文片段不在需求文本中"


def test_multi_label_classification():
    s = build(_req("虚拟机太多管理麻烦，希望放到云上统一管，作业排队太久"))
    labels = {p["label"] for p in s["requirement_points"]}
    assert "ops_efficiency" in labels, "应识别运维管理效率"
    assert "migration" in labels, "应识别资源迁移"
    assert "scheduling" in labels, "应识别作业调度"
    assert len(labels) >= 3, "一条诉求应命中多个需求点，实际 %s" % labels


def test_compliance_detected():
    s = build(_req("数据都在他们机房，暂时不上公有云，这是硬要求"))
    labels = {p["label"] for p in s["requirement_points"]}
    assert "compliance" in labels


def test_competitor_detected():
    s = build(_req("他们问华为云、阿里的同类产品我们能不能对标讲讲"))
    assert any(p["label"] == "competitor" for p in s["requirement_points"])


# ---------------- 不编数字 ----------------

def test_expected_metrics_stays_not_found():
    """核心纪律：需求原文没给指标就不填数字。"""
    s = build(_req("希望提升性能"))
    assert s["expected_metrics"] == NOT_FOUND
    assert "不编数字" in s["_note"]


def test_priority_stays_pending():
    s = build(_req("希望提升性能"))
    assert s["priority"] == PENDING


def test_missing_industry_is_pending_not_guessed():
    s = build(_req("希望提升性能"))
    assert s["customer_industry"] == PENDING, "缺行业应填待补充，不猜"


def test_no_recognized_point_raises():
    """识别不出需求点时拒绝生成空壳说明书。"""
    with pytest.raises(RequirementError) as e:
        build(_req("asdfghjkl"))
    assert "空壳" in str(e.value)


def test_empty_text_raises():
    with pytest.raises(RequirementError):
        build(_req("   "))


def test_missing_field_raises():
    with pytest.raises(RequirementError):
        build({"id": "T"})


# ---------------- 完整率 ----------------

def test_completeness_is_measurable():
    s = build(_req("管理麻烦，希望统一管"))
    q = s["_quality"]
    assert q["required_total"] == len(REQUIRED_FIELDS)
    assert 0 < q["completeness"] < 1, "缺字段时完整率应在 0 与 1 之间"
    assert len(q["missing_fields"]) == q["required_total"] - q["required_filled"]
    assert "澄清进度" in q["note"], "完整率须说明是澄清进度不是文档质量"


def test_industry_fills_completeness():
    without = build(_req("管理麻烦"))["_quality"]["completeness"]
    with_ind = build(_req("管理麻烦", industry="政务"))["_quality"]["completeness"]
    assert with_ind > without, "填了行业完整率应上升"


def test_source_metadata_kept():
    s = build(_req("管理麻烦", channel="客户现场", received_at="2026-09-08",
                   reporter="售前"))
    assert s["source"]["channel"] == "客户现场"
    assert s["source"]["reporter"] == "售前"


def test_classify_returns_ordered_ids():
    points = classify("管理麻烦，希望统一管，作业排队")
    ids = [p["id"] for p in points]
    assert ids == ["RP-%02d" % (i + 1) for i in range(len(points))]
