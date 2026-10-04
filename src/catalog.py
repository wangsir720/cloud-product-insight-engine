# -*- coding: utf-8 -*-
"""数据目录加载：云产品矩阵、原始需求、行业动态。

三条纪律与本项目其他部分一致：

1. **缺列、缺 source_id、未知 credibility 直接抛错**，不静默兜底。
2. **空字段归一为 None**，绝不返回 0 或空串顶替 —— 「未查到」与「无」是两件事。
3. 数据表外置为 CSV/JSON，改数据不用改代码。
"""
from __future__ import annotations

import csv
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PRODUCT_CSV = os.path.join(DATA_DIR, "products", "cloud_product_matrix.csv")
REQUEST_JSON = os.path.join(DATA_DIR, "requests", "raw_requests.json")
TREND_JSON = os.path.join(DATA_DIR, "trends", "industry_trends.json")

CREDIBILITY_ORDER = {"unverified": 0, "secondary": 1, "official": 2}

# B-01 登记的五层产品（JD 职责 1 原文点名）
LAYERS = ["IaaS", "PaaS", "DAAS", "MASS", "SaaS"]
LAYER_LABEL = {
    "IaaS": "基础设施即服务",
    "PaaS": "平台即服务",
    "DAAS": "数据即服务",
    "MASS": "异构算力即服务",
    "SaaS": "软件即服务",
}

# B-02 登记的能力域
CATEGORY_LABEL = {
    "compute": "通用计算",
    "gpu": "GPU 算力",
    "hpc": "HPC 高性能计算",
    "storage": "存储",
    "network": "网络",
    "container": "容器",
    "database": "数据库",
    "bigdata": "大数据",
    "ai_platform": "AI 平台",
    "serverless": "Serverless",
    "search": "检索",
}

VENDOR_LABEL = {
    "Sugon": "曙光先进计算机",
    "HuaweiCloud": "华为云",
    "Aliyun": "阿里云",
    "TencentCloud": "腾讯云",
}

NOT_FOUND = "未查到"


class CatalogError(Exception):
    """目录数据缺失或格式错误。"""


class Row:
    def __init__(self, data: dict, key_field: str = "product_name"):
        self.data = data
        self.key_field = key_field

    @property
    def key(self) -> str:
        return (self.data.get(self.key_field) or "").strip()

    @property
    def source_id(self) -> str:
        return (self.data.get("source_id") or "").strip()

    @property
    def credibility(self) -> str:
        return (self.data.get("credibility") or "").strip()

    @property
    def vendor(self) -> str:
        return (self.data.get("vendor") or "").strip()

    @property
    def layer(self) -> str:
        return (self.data.get("layer") or "").strip()

    @property
    def category(self) -> str:
        return (self.data.get("category_key") or "").strip()

    @property
    def found(self) -> bool:
        """该行是否为有效产品条目。

        占位行（产品名写「未查到」或「-」）**不算覆盖** ——
        曙光云的 SaaS 行就是占位：官网未公开该产品线，写上它会让矩阵虚高。
        """
        return bool(self.key) and self.key not in (NOT_FOUND, "-")

    def s(self, field: str):
        v = (self.data.get(field) or "").strip()
        return v if v and v != "-" else None

    def cite(self) -> str:
        return "%s（来源 %s，可信度 %s）" % (
            self.vendor + "/" + self.key, self.source_id, self.credibility)


def load_products() -> list[Row]:
    if not os.path.isfile(PRODUCT_CSV):
        raise CatalogError("数据文件不存在：%s" % PRODUCT_CSV)
    with open(PRODUCT_CSV, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise CatalogError("数据文件为空：%s" % PRODUCT_CSV)
    for r in rows:
        for req in ("vendor", "layer", "source_id", "credibility"):
            if not (r.get(req) or "").strip():
                raise CatalogError("数据行缺少 %s：%s" % (req, PRODUCT_CSV))
        if r["credibility"].strip() not in CREDIBILITY_ORDER:
            raise CatalogError("未知 credibility %r" % r["credibility"].strip())
        if r["layer"].strip() not in LAYERS:
            raise CatalogError("未知产品层 %r，应为 %s" % (r["layer"].strip(), LAYERS))
    return [Row(r) for r in rows]


def vendors() -> list[str]:
    seen = []
    for r in load_products():
        if r.vendor not in seen:
            seen.append(r.vendor)
    return sorted(seen)


def load_requests() -> list[dict]:
    if not os.path.isfile(REQUEST_JSON):
        raise CatalogError("数据文件不存在：%s" % REQUEST_JSON)
    with open(REQUEST_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("requests") if isinstance(data, dict) else data
    if not rows:
        raise CatalogError("原始需求集为空")
    for r in rows:
        for req in ("id", "raw_text"):
            if req not in r:
                raise CatalogError("原始需求缺少字段 %s" % req)
    return rows


def load_trends() -> list[dict]:
    if not os.path.isfile(TREND_JSON):
        return []
    with open(TREND_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("trends") if isinstance(data, dict) else data
