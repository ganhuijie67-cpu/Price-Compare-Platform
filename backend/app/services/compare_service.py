from datetime import datetime
from typing import Any
from uuid import uuid4

from app.adapters.mock_platform import MockPlatformAdapter
from app.schemas.compare import CompareRequest
from app.tools.compare_rank import CompareRankTool
from app.tools.product_match import ProductMatchTool
from app.tools.product_parse import ProductParseTool


# 这两个工具先作为模块级单例复用：
# 1. 当前实现是无状态的，复用对象不会引入并发问题；
# 2. service 调用时不用每次都重新实例化，代码也更简洁。
MOCK_PLATFORM_ADAPTER = MockPlatformAdapter()
PRODUCT_PARSE_TOOL = ProductParseTool()
PRODUCT_MATCH_TOOL = ProductMatchTool()
COMPARE_RANK_TOOL = CompareRankTool()


def compare_products(request: CompareRequest) -> dict[str, Any]:
    """读取 Mock 商品数据，并组装文档约定的比价接口响应。"""

    # 平台查询逻辑已经拆到 MockPlatformAdapter：
    # 1. service 不再关心 mock 文件放在哪里；
    # 2. 后续如果接真实平台 API，这里更容易替换成新的 adapter；
    # 3. service 只保留“编排流程”的职责。
    candidate_items = MOCK_PLATFORM_ADAPTER.search(
        request.platforms,
        request.max_results_per_platform,
    )

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

    # `parsed_product` 保留了内部匹配逻辑需要的字段，例如 category；
    # 所以匹配阶段仍然使用内部解析结构，而不是上面的 normalized_product。
    matched_items = PRODUCT_MATCH_TOOL.match_items(parsed_product, candidate_items)

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
    # 具体排序和最低价规则交给 CompareRankTool，service 只负责串流程。
    summary = COMPARE_RANK_TOOL.build_summary(response_items, updated_at)

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
