import json
from pathlib import Path
from typing import Any

from app.tools.product_match import ProductMatchTool
from app.tools.product_parse import ProductParseTool


# 当前文件在 backend/app/services/ 下，parents[3] 回到项目根目录。
PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMPARE_MOCK_PATH = PROJECT_ROOT / "mock_data" / "platform_products" / "compare_mock.json"
PRODUCT_PARSE_TOOL = ProductParseTool()
PRODUCT_MATCH_TOOL = ProductMatchTool()


def compare_products(query: str) -> dict[str, Any]:
    """读取 Mock 商品数据，并组装比价接口响应。"""

    mock_data = _load_compare_mock()

    # 第一步：把用户输入的自然语言商品名解析成结构化信息。
    # 例如：iPhone 17 Pro 256GB 国行 -> model/capacity/version/category。
    normalized_product = PRODUCT_PARSE_TOOL.parse(query)

    # 第二步：用解析结果去判断 Mock 商品列表里哪些是真同款。
    # 这里会给每个 item 追加 match_score、match_reasons、is_match。
    matched_items = PRODUCT_MATCH_TOOL.match_items(normalized_product, mock_data["items"])

    return {
        "query": query,
        "normalized_product": normalized_product,
        "items": matched_items,
    }


def _load_compare_mock() -> dict[str, Any]:
    """从 mock_data 目录读取当前阶段使用的固定商品数据。"""

    with COMPARE_MOCK_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)
