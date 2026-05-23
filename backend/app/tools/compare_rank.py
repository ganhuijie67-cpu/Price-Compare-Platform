from typing import Any


class CompareRankTool:
    """负责比价结果里的最低价、推荐平台和 summary 聚合。"""

    def build_summary(
        self,
        items: list[dict[str, Any]],
        updated_at: str,
    ) -> dict[str, Any]:
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
        lowest_item = min(items, key=self._item_sort_price)
        recommended_item = min(items, key=self._recommendation_sort_key)

        return {
            # lowest_price 优先取券后价，没有券后价时再回退到标价。
            "lowest_price": self._item_effective_price(lowest_item),
            "lowest_platform": lowest_item.get("platform"),
            "recommended_platform": recommended_item.get("platform"),
            "result_count": len(items),
            "updated_at": updated_at,
        }

    def _recommendation_sort_key(self, item: dict[str, Any]) -> tuple[float, int, float]:
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
            self._item_sort_price(item),
        )

    def _item_sort_price(self, item: dict[str, Any]) -> float:
        """把价格统一成可比较的数值。"""

        # 先拿到“实际比较价”。
        # 如果 item 没有价格，就返回正无穷，让它在排序时自然排到最后。
        price = self._item_effective_price(item)
        return float(price) if price is not None else float("inf")

    def _item_effective_price(self, item: dict[str, Any]) -> Any:
        """优先使用券后价，没有时回退到商品标价。"""

        # 券后价比原价更接近用户真实成交价，所以优先拿 coupon_price。
        return item.get("coupon_price") or item.get("price")
