import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.schemas.compare import CompareRequest
from app.tools.product_match import ProductMatchTool
from app.tools.product_parse import ProductParseTool


# 当前文件在 backend/app/services/ 下，parents[3] 回到项目根目录。
PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMPARE_MOCK_PATH = PROJECT_ROOT / "mock_data" / "platform_products" / "compare_mock.json"

# 这两个工具先作为模块级单例复用：
# 1. 当前实现是无状态的，复用对象不会引入并发问题；
# 2. service 调用时不用每次都重新实例化，代码也更简洁。
PRODUCT_PARSE_TOOL = ProductParseTool()
PRODUCT_MATCH_TOOL = ProductMatchTool()


def compare_products(request: CompareRequest) -> dict[str, Any]:
    """读取 Mock 商品数据，并组装文档约定的比价接口响应。"""

    # 先把固定 Mock 数据读出来。
    # 当前 compare 还没有接真实平台，所以所有候选商品都来自这份本地文件。
    mock_data = _load_compare_mock()

    # 整个响应里的时间字段统一复用同一个时间戳，
    # 这样 summary.updated_at 和 item.updated_at 就不会出现几毫秒级的偏差。
    updated_at = _current_timestamp()

    # 第一步：把用户输入的自然语言商品名解析成结构化信息。
    # 例如：iPhone 17 Pro 256GB 国行 -> model/capacity/version/category。
    parsed_product = PRODUCT_PARSE_TOOL.parse(request.query)

    # 文档里的 normalized_product 结构，和内部解析结构并不完全一致。
    # 这里做一次显式映射，把接口返回字段稳定下来：
    # 1. `name` 对齐文档；
    # 2. `color` 当前解析器还没有能力识别，先明确返回 null；
    # 3. 不把内部 `category` 直接暴露给 compare 响应，避免先暴露后又改。
    normalized_product = {
        "brand": parsed_product.get("brand"),
        "name": parsed_product.get("model") or request.query,
        "model": parsed_product.get("model"),
        "capacity": parsed_product.get("capacity"),
        "version": parsed_product.get("version"),
        "color": None,
    }

    # 第二步：用解析结果去判断 Mock 商品列表里哪些是真同款。
    # 这里会给每个 item 追加 match_score、match_reasons、is_match。

    # 先按请求里的平台和每平台最大返回数做一轮筛选，
    # 尽量让后续匹配逻辑只处理“这次真正需要返回”的候选商品。
    filtered_items = _filter_items(
        mock_data["items"],
        request.platforms,
        request.max_results_per_platform,
    )

    # `parsed_product` 保留了内部匹配逻辑需要的字段，例如 category；
    # 所以匹配阶段仍然使用内部解析结构，而不是上面的 normalized_product。
    matched_items = PRODUCT_MATCH_TOOL.match_items(parsed_product, filtered_items)

    # 把内部 match 结果逐条转换成接口文档里的 items 数组结构。
    # 这里会补默认值、字段名映射，以及一些当前阶段的衍生字段。
    response_items = [
        _build_response_item(
            item=item,
            index=index,
            updated_at=updated_at,
            enable_risk_analysis=request.enable_risk_analysis,
        )
        for index, item in enumerate(matched_items, start=1)
    ]

    # summary 是对 items 的聚合视图，例如最低价、推荐平台和结果总数。
    summary = _build_summary(response_items, updated_at)

    # 最外层响应结构按 docs/api.md 的通用成功格式返回：
    # success / data / message / request_id。
    return {
        "success": True,
        "data": {
            # query_id 代表这次比价查询本身的唯一标识。
            # 现在还没落库，所以先生成一个临时 ID 给前端联调使用。
            "query_id": _build_query_id(),
            "normalized_product": normalized_product,
            "summary": summary,
            "items": response_items,

            # agent_trace 当前还是占位的最小版本。
            # 先把字段结构立住，后面真正接工作流时可以平滑替换成真实耗时数据。
            "agent_trace": [
                {"node": "parse_query", "status": "success", "duration_ms": 12},
                {"node": "product_match", "status": "success", "duration_ms": 18},
                {"node": "build_response", "status": "success", "duration_ms": 6},
            ],
            "buying_advice": _build_buying_advice(summary),
        },
        "message": "ok",
        "request_id": _build_request_id(),
    }


def _load_compare_mock() -> dict[str, Any]:
    """从 mock_data 目录读取当前阶段使用的固定商品数据。"""

    # 明确使用 UTF-8 读取，避免中文标题在不同开发环境下出现乱码。
    with COMPARE_MOCK_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _filter_items(
    items: list[dict[str, Any]],
    platforms: list[str],
    max_results_per_platform: int,
) -> list[dict[str, Any]]:
    """按请求参数筛选候选商品。"""

    # 如果请求里没有传 platforms，这里会得到空集合。
    # 后面的判断逻辑会把空集合解释成“不过滤平台”。
    platform_filter = set(platforms)

    # 记录每个平台已经保留了多少条结果。
    # 这样可以实现“每个平台最多返回 N 条”的限制。
    results_per_platform: dict[str, int] = {}
    filtered_items: list[dict[str, Any]] = []

    for item in items:
        # Mock 数据里如果没写平台，默认按 mock 平台处理，
        # 这样能保证响应里至少有一个明确的平台值。
        platform = item.get("platform", "mock")

        # 只有在用户显式传了 platforms 时才启用平台过滤。
        # `platform_filter` 为空时，这里会直接放行全部商品。
        if platform_filter and platform not in platform_filter:
            continue

        current_count = results_per_platform.get(platform, 0)

        # 超过每个平台的上限后，继续扫描后面的商品，但不再收下当前平台的新结果。
        if current_count >= max_results_per_platform:
            continue

        # 先更新计数，再把商品加入最终返回列表。
        results_per_platform[platform] = current_count + 1
        filtered_items.append(item)

    return filtered_items


def _build_response_item(
    item: dict[str, Any],
    index: int,
    updated_at: str,
    enable_risk_analysis: bool,
) -> dict[str, Any]:
    """把内部匹配结果转换成文档里的 items 结构。"""

    # 文档里要求返回 risk_tags。
    # 但当前请求允许前端显式关闭风险分析，所以这里按开关决定是否输出风险结果。
    risk_tags = item.get("risk_tags", []) if enable_risk_analysis else []

    # 内部匹配逻辑产出的是 `match_reasons` 列表，
    # 接口文档里需要的是单个 `recommendation_reason` 字符串，
    # 所以这里先把原始原因收集起来，后面再拼接成一句话。
    recommendation_reasons = list(item.get("match_reasons", []))

    # 当前阶段先用一条简单的补充说明，把“风险”或“低风险”信息并入推荐原因里。
    if risk_tags:
        recommendation_reasons.append("存在风险标签，建议下单前再次确认")
    else:
        recommendation_reasons.append("匹配度较高，风险较低")

    return {
        "platform": item.get("platform"),

        # 文档里要求每个商品有 platform_product_id。
        # Mock 数据目前没有这个字段，所以先按“平台 + 顺序号”补一个稳定占位值。
        "platform_product_id": item.get("platform_product_id")
        or f"{item.get('platform', 'mock')}_mock_{index:03d}",
        "title": item.get("title"),
        "price": item.get("price"),
        "coupon_price": item.get("coupon_price"),

        # 现阶段默认全部按人民币处理。
        # 等后续接入跨境或多币种平台时，再改成真实来源数据。
        "currency": item.get("currency", "CNY"),
        "shop_name": item.get("shop_name"),

        # Mock 数据并没有完整提供店铺类型，
        # 所以这里用店铺名称做一次最小推断，保证字段先存在。
        "shop_type": item.get("shop_type") or _infer_shop_type(item.get("shop_name")),
        "product_url": item.get("product_url"),
        "image_url": item.get("image_url"),
        "match_score": item.get("match_score", 0.0),
        "risk_tags": risk_tags,

        # 风险分析关闭时，risk_level 也跟着返回 null，
        # 避免出现“没有风险标签，但却给了一个 low/medium/high”的误导结果。
        "risk_level": _build_risk_level(risk_tags) if enable_risk_analysis else None,
        "recommendation_reason": "，".join(recommendation_reasons),
        "updated_at": updated_at,
    }


def _build_summary(items: list[dict[str, Any]], updated_at: str) -> dict[str, Any]:
    """生成接口文档中的 summary 结构。"""

    # 没有命中任何候选商品时，依然返回结构完整的 summary，
    # 这样前端就不用对“summary 缺失”和“summary 存在但为空”写两套逻辑。
    if not items:
        return {
            "lowest_price": None,
            "lowest_platform": None,
            "recommended_platform": None,
            "result_count": 0,
            "updated_at": updated_at,
        }

    # 最低价和推荐平台是两个不同概念：
    # 1. lowest_* 纯看价格；
    # 2. recommended_* 综合匹配度、风险和价格。
    lowest_item = min(items, key=_item_sort_price)
    recommended_item = min(items, key=_recommendation_sort_key)

    return {
        # lowest_price 优先取券后价，没有券后价时再回退到标价。
        "lowest_price": _item_effective_price(lowest_item),
        "lowest_platform": lowest_item.get("platform"),
        "recommended_platform": recommended_item.get("platform"),
        "result_count": len(items),
        "updated_at": updated_at,
    }


def _build_buying_advice(summary: dict[str, Any]) -> str:
    """生成当前阶段的最小购买建议文案。"""

    lowest_platform = summary.get("lowest_platform")
    recommended_platform = summary.get("recommended_platform")

    # 一个候选都没有时，直接告诉前端这是“无结果建议”，
    # 避免前端再自己猜为什么没有推荐平台。
    if not lowest_platform:
        return "当前没有找到可比较的候选商品，建议换一个更完整的商品名称重试。"

    # 如果最低价平台和推荐平台是同一个，说明不需要在“更便宜”和“更稳妥”之间做取舍。
    if lowest_platform == recommended_platform:
        return f"{recommended_platform} 当前价格和匹配度都更优，建议优先查看。"

    # 否则就明确告诉用户：谁最便宜、谁更推荐。
    return (
        f"{lowest_platform} 当前价格最低；"
        f"{recommended_platform} 在匹配度和风险上更稳，建议综合售后与价格再决定。"
    )


def _build_risk_level(risk_tags: list[str]) -> str:
    """根据风险标签数量给出最小风险等级。"""

    # 当前版本先用最简单的规则兜底：
    # 0 个风险标签 -> low
    # 1 个风险标签 -> medium
    # 2 个及以上风险标签 -> high
    # 这不是最终算法，只是为了先把文档字段跑通。
    if not risk_tags:
        return "low"
    if len(risk_tags) == 1:
        return "medium"
    return "high"


def _infer_shop_type(shop_name: Any) -> str | None:
    """根据店铺名称推断店铺类型。"""

    # 店铺名缺失或不是字符串时，直接返回 None，
    # 比瞎猜一个默认值更安全。
    if not isinstance(shop_name, str):
        return None

    # 先用中文关键词做最小推断。
    # 当前主要服务于 Mock 数据，所以规则可以先保持简单。
    if "自营" in shop_name:
        return "self_operated"
    if "旗舰店" in shop_name or "官方" in shop_name:
        return "official_flagship"
    return "marketplace"


def _recommendation_sort_key(item: dict[str, Any]) -> tuple[float, int, float]:
    """优先更高匹配度、更低风险和更低价格。"""

    # 先把风险等级映射成可排序的整数。
    # 数字越小代表风险越低，也就越应该排在前面。
    risk_rank = {
        "low": 0,
        "medium": 1,
        "high": 2,
        None: 3,
    }

    # `min(..., key=...)` 会选择“最小”的那一项。
    # 所以这里把 match_score 取负数，等价于“分数越高越优先”。
    # 排序优先级依次是：
    # 1. 匹配分更高
    # 2. 风险更低
    # 3. 价格更低
    return (
        -float(item.get("match_score", 0.0)),
        risk_rank.get(item.get("risk_level"), 3),
        _item_sort_price(item),
    )


def _item_sort_price(item: dict[str, Any]) -> float:
    """把价格统一成可比较的数值。"""

    # 先拿到“实际比较价”。
    # 如果 item 没有价格，就返回正无穷，让它在排序时自然排到最后。
    price = _item_effective_price(item)
    return float(price) if price is not None else float("inf")


def _item_effective_price(item: dict[str, Any]) -> Any:
    """优先使用券后价，没有时回退到商品标价。"""

    # 券后价比原价更接近用户真实成交价，所以优先拿 coupon_price。
    return item.get("coupon_price") or item.get("price")


def _current_timestamp() -> str:
    """返回带时区的当前时间字符串。"""

    # 直接输出 ISO 8601 带时区格式，方便前后端统一解析。
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _build_query_id() -> str:
    """生成最小可用的 query_id。"""

    # 先用 UUID 前 8 位做一个轻量级占位 ID。
    # 后续接数据库后，这里可以替换成真实主键或业务编号。
    return f"cq_{uuid4().hex[:8]}"


def _build_request_id() -> str:
    """生成最小可用的 request_id。"""

    # request_id 和 query_id 分开生成：
    # 1. request_id 代表一次 HTTP 请求；
    # 2. query_id 代表一次比价查询结果。
    # 现在两者都还是临时实现，但语义先区分开更稳妥。
    return f"req_{uuid4().hex[:8]}"
