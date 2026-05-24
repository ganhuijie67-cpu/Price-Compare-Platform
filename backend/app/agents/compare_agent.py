from datetime import datetime
from typing import Any
from uuid import uuid4

from app.adapters.mock_platform import MockPlatformAdapter
from app.schemas.compare import CompareRequest
from app.tools.compare_rank import CompareRankTool
from app.tools.product_match import ProductMatchTool
from app.tools.product_parse import ProductParseTool


class CompareAgent:
    """不用 LangGraph 的最小比价编排层。"""

    def __init__(
        self,
        platform_adapter: MockPlatformAdapter | None = None,
        product_parse_tool: ProductParseTool | None = None,
        product_match_tool: ProductMatchTool | None = None,
        compare_rank_tool: CompareRankTool | None = None,
    ) -> None:
        """初始化比价流程需要的 adapter 和工具。"""

        # 这些依赖都允许从外部传入，方便单测或后续替换真实平台 adapter。
        self.platform_adapter = platform_adapter or MockPlatformAdapter()
        self.product_parse_tool = product_parse_tool or ProductParseTool()
        self.product_match_tool = product_match_tool or ProductMatchTool()
        self.compare_rank_tool = compare_rank_tool or CompareRankTool()

    def run(self, request: CompareRequest) -> dict[str, Any]:
        """执行完整比价流程，并返回接口文档约定的响应结构。"""

        # platform_search：从平台适配器拿候选商品。
        # 当前 adapter 读取本地 mock 文件，后续可以替换成真实平台 API。
        candidate_items = self.platform_adapter.search(
            request.platforms,
            request.max_results_per_platform,
        )

        # 整个响应里的时间字段统一复用同一个时间戳，
        # 这样 summary.updated_at 和 item.updated_at 就不会出现几毫秒级的偏差。
        updated_at = self._current_timestamp()

        # parse_product：把用户输入的自然语言商品名解析成结构化信息。
        # 例如：iPhone 17 Pro 256GB 国行 -> model/capacity/version/category。
        parsed_product = self.product_parse_tool.parse(request.query)
        normalized_product = self._build_normalized_product(parsed_product, request.query)

        # product_match：用解析结果判断平台候选商品是否同款。
        # 这里会给每个 item 追加 match_score、match_reasons、is_match。
        matched_items = self.product_match_tool.match_items(
            parsed_product,
            candidate_items,
        )

        # build_response_items：把内部 match 结果转换成接口文档里的 items 结构。
        response_items = [
            self._build_response_item(
                item=item,
                index=index,
                updated_at=updated_at,
                enable_risk_analysis=request.enable_risk_analysis,
            )
            for index, item in enumerate(matched_items, start=1)
        ]

        # rank_summary：最低价、推荐平台、结果数量都交给 CompareRankTool 聚合。
        summary = self.compare_rank_tool.build_summary(response_items, updated_at)

        return {
            "success": True,
            "data": {
                # query_id 代表这次比价查询本身的唯一标识。
                # 现在还没落库，所以先生成一个临时 ID 给前端联调使用。
                "query_id": self._build_query_id(),
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
                "buying_advice": self._build_buying_advice(summary),
            },
            "message": "ok",
            "request_id": self._build_request_id(),
        }

    def _build_normalized_product(
        self,
        parsed_product: dict[str, Any],
        query: str,
    ) -> dict[str, Any]:
        """把内部解析结果映射成接口文档里的 normalized_product。"""

        # 文档里的 normalized_product 结构，和内部解析结构并不完全一致。
        # 这里做一次显式映射，把接口返回字段稳定下来。
        return {
            "brand": parsed_product.get("brand"),
            "name": parsed_product.get("model") or query,
            "model": parsed_product.get("model"),
            "capacity": parsed_product.get("capacity"),
            "version": parsed_product.get("version"),
            "color": None,
        }

    def _build_response_item(
        self,
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
        # 接口文档里需要的是单个 `recommendation_reason` 字符串。
        recommendation_reasons = list(item.get("match_reasons", []))

        if risk_tags:
            recommendation_reasons.append("存在风险标签，建议下单前再次确认")
        else:
            recommendation_reasons.append("匹配度较高，风险较低")

        return {
            "platform": item.get("platform"),
            "platform_product_id": item.get("platform_product_id")
            or f"{item.get('platform', 'mock')}_mock_{index:03d}",
            "title": item.get("title"),
            "price": item.get("price"),
            "coupon_price": item.get("coupon_price"),
            "currency": item.get("currency", "CNY"),
            "shop_name": item.get("shop_name"),
            "shop_type": item.get("shop_type") or self._infer_shop_type(item.get("shop_name")),
            "product_url": item.get("product_url"),
            "image_url": item.get("image_url"),
            "match_score": item.get("match_score", 0.0),
            "risk_tags": risk_tags,
            "risk_level": self._build_risk_level(risk_tags) if enable_risk_analysis else None,
            "recommendation_reason": "，".join(recommendation_reasons),
            "updated_at": updated_at,
        }

    def _build_buying_advice(self, summary: dict[str, Any]) -> str:
        """生成当前阶段的最小购买建议文案。"""

        lowest_platform = summary.get("lowest_platform")
        recommended_platform = summary.get("recommended_platform")

        # 一个候选都没有时，直接告诉前端这是“无结果建议”。
        if not lowest_platform:
            return "当前没有找到可比较的候选商品，建议换一个更完整的商品名称重试。"

        # 最低价平台和推荐平台相同时，不需要在“更便宜”和“更稳妥”之间做取舍。
        if lowest_platform == recommended_platform:
            return f"{recommended_platform} 当前价格和匹配度都更优，建议优先查看。"

        return (
            f"{lowest_platform} 当前价格最低；"
            f"{recommended_platform} 在匹配度和风险上更稳，建议综合售后与价格再决定。"
        )

    def _build_risk_level(self, risk_tags: list[str]) -> str:
        """根据风险标签数量给出最小风险等级。"""

        # 当前版本先用最简单的规则兜底，后续真实风险分析可以替换这里。
        if not risk_tags:
            return "low"
        if len(risk_tags) == 1:
            return "medium"
        return "high"

    def _infer_shop_type(self, shop_name: Any) -> str | None:
        """根据店铺名称推断店铺类型。"""

        if not isinstance(shop_name, str):
            return None
        if "自营" in shop_name:
            return "self_operated"
        if "旗舰店" in shop_name or "官方" in shop_name:
            return "official_flagship"
        return "marketplace"

    def _current_timestamp(self) -> str:
        """返回带时区的当前时间字符串。"""

        return datetime.now().astimezone().isoformat(timespec="seconds")

    def _build_query_id(self) -> str:
        """生成最小可用的 query_id。"""

        return f"cq_{uuid4().hex[:8]}"

    def _build_request_id(self) -> str:
        """生成最小可用的 request_id。"""

        return f"req_{uuid4().hex[:8]}"
