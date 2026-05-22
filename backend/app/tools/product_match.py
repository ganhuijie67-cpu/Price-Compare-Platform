from typing import Any


# 这些关键词通常说明商品不是手机本体，而是配件。
# 只要标题命中这里的任意词，就直接判定为“不是同款”。
ACCESSORY_KEYWORDS = ("手机壳", "贴膜", "保护套")

# 这些关键词说明商品可能不是全新正常零售机。
# 第一版先不直接排除，只降低匹配分，并给前端一个原因提示。
USED_KEYWORDS = ("二手", "99新", "官换", "资源机")


class ProductMatchTool:
    """同款匹配工具的最小规则版本。"""

    def match_items(
        self,
        parsed_product: dict[str, Any],
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """给每个商品追加同款匹配结果。"""

        # items 是 Mock 平台返回的商品列表。
        # 这里逐个调用 match_item，给每个商品都加上：
        # match_score、match_reasons、is_match。
        return [self.match_item(parsed_product, item) for item in items]

    def match_item(
        self,
        parsed_product: dict[str, Any],
        item: dict[str, Any],
    ) -> dict[str, Any]:
        """按标题规则判断单个商品是否与用户查询同款。"""

        # 当前最小版本只看商品标题。
        # 后续如果 Mock 数据里有 SKU、类目、属性字段，可以再用那些字段做更准判断。
        title = item.get("title", "")
        title_lower = title.lower()

        # 配件要优先判断。
        # 例如 “iPhone 17 Pro 手机壳” 虽然标题包含型号，但它不是手机本体。
        if self._contains_any(title, ACCESSORY_KEYWORDS):
            return {
                # **item 表示保留原商品里的所有字段，例如 platform/title/price。
                **item,
                "match_score": 0.0,
                "match_reasons": ["配件商品，不是主商品"],
                "is_match": False,
            }

        # score 是匹配分，reasons 是给前端展示的匹配原因。
        # 当前总分最高是 0.95：型号 0.45 + 容量 0.25 + 版本 0.25。
        score = 0.0
        reasons: list[str] = []

        # 型号是最核心条件，例如 iPhone 17 Pro。
        # 标题里包含型号，说明大概率是同一个商品系列。
        model = parsed_product.get("model")
        if model and model.lower() in title_lower:
            score += 0.45
            reasons.append("型号一致")

        # 容量会影响价格和是否同款，例如 128GB 和 256GB 不能混在一起。
        capacity = parsed_product.get("capacity")
        if capacity and capacity.lower() in title_lower:
            score += 0.25
            reasons.append("容量一致")

        # 版本也会影响购买风险，例如国行、港版、美版的保修和网络支持不同。
        version = parsed_product.get("version")
        if version and version in title:
            score += 0.25
            reasons.append("版本一致")

        # 二手、99新、官换、资源机仍可能是同型号同容量，
        # 但它们不是“全新普通零售机”，所以降低分数并提示需要确认。
        if self._contains_any(title, USED_KEYWORDS):
            score = max(score - 0.2, 0.0)
            reasons.append("成色或来源需要确认")

        # 四舍五入到两位小数，接口返回更稳定，也方便前端展示。
        match_score = round(score, 2)

        return {
            **item,
            "match_score": match_score,
            "match_reasons": reasons,
            # 第一版先用 0.7 作为同款阈值。
            # 例如型号一致 + 版本一致 = 0.7，可以先认为是同款候选。
            "is_match": match_score >= 0.7,
        }

    def _contains_any(self, title: str, keywords: tuple[str, ...]) -> bool:
        """判断标题是否包含任意关键词。"""

        # any(...) 只要有一个关键词命中就返回 True。
        return any(keyword in title for keyword in keywords)
