#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""命令行入口：原始需求 -> 需求说明书 + 竞品对标矩阵 + 技术交流材料 + 周月报。

    python -m src.cli                # 全流程
    python -m src.cli --competitor   # 只出竞品对标报告
    python -m src.cli --period 月报   # 指定报告周期
"""
from __future__ import annotations

import argparse
import os
import sys

from .catalog import load_requests
from .competitor_matrix import build_matrix
from .doc_assembler import (render_competitor_report, render_prd, render_report,
                            render_tech_talk, save, save_csv, save_json)
from .report_builder import build as build_report
from .requirement_builder import build as build_spec

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT, "output")

ARTIFACTS = ["prd_draft.md", "competitor_report.md", "tech_talk.md",
             "weekly_report.md", "competitor_matrix.csv", "result.json"]


def run(period: str = "周报") -> dict:
    requests = load_requests()
    specs = [build_spec(r) for r in requests]
    data = build_matrix()
    report = build_report(specs, data, period)

    main_spec = specs[0] if specs else None
    save(render_prd(main_spec), os.path.join(OUTPUT_DIR, "prd_draft.md"))
    save(render_competitor_report(data),
         os.path.join(OUTPUT_DIR, "competitor_report.md"))
    save(render_tech_talk(main_spec, data),
         os.path.join(OUTPUT_DIR, "tech_talk.md"))
    save(render_report(report), os.path.join(OUTPUT_DIR, "weekly_report.md"))

    rows = []
    for v in data["vendors"]:
        for l in data["layers"]:
            cell = data["matrix"][v][l]
            if cell["count"] == 0:
                rows.append([v, l, "未查到", "", "", ""])
            else:
                for p in cell["products"]:
                    rows.append([v, l, p["name"], p["category_label"],
                                 p["positioning"], p["cite"]])
    save_csv(rows, ["厂商", "云产品层", "产品名", "能力域", "定位", "来源"],
             os.path.join(OUTPUT_DIR, "competitor_matrix.csv"))

    save_json({"requirements": specs, "competitor": data, "report": report},
              os.path.join(OUTPUT_DIR, "result.json"))
    return {"specs": specs, "competitor": data, "report": report}


def _summary(res: dict) -> None:
    specs, data, report = res["specs"], res["competitor"], res["report"]
    cov = data["coverage"]
    print("需求 %d 条 ｜ 需求点 %d 个 ｜ 平均完整率 %.0f%%"
          % (len(specs), report["kpi"][1]["value"],
             report["kpi"][2]["value"] * 100))
    print("竞品矩阵：产品 %d 条 ｜ 厂商覆盖 %.0f%% ｜ 层覆盖 %.0f%% ｜ 能力域覆盖 %.0f%%"
          % (data["product_count"], cov["vendor_rate"] * 100,
             cov["layer_rate"] * 100, cov["category_rate"] * 100))
    print("空白项 %d 格（未查到公开产品的厂商×层组合）" % data["gap_count"])
    print("已生成：output/{%s}" % ", ".join(ARTIFACTS))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="src.cli", description="云计算产品需求洞察与竞品对标引擎")
    ap.add_argument("--competitor", action="store_true", help="只生成竞品对标报告")
    ap.add_argument("--period", default="周报", help="报告周期，默认周报")
    args = ap.parse_args(argv)

    try:
        if args.competitor:
            data = build_matrix()
            save(render_competitor_report(data),
                 os.path.join(OUTPUT_DIR, "competitor_report.md"))
            print("已生成：output/competitor_report.md")
            cov = data["coverage"]
            print("厂商 %d 家 ｜ 产品 %d 条 ｜ 层覆盖 %.0f%% ｜ 空白项 %d 格"
                  % (len(data["vendors"]), data["product_count"],
                     cov["layer_rate"] * 100, data["gap_count"]))
            return 0
        _summary(run(args.period))
    except Exception as e:
        print("执行失败：%s: %s" % (type(e).__name__, e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
