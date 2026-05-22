from typing import Literal

from pydantic import BaseModel, Field, field_validator


# 先把文档里出现的平台枚举固定下来。
# 这样做的好处是：
# 1. 前端传错平台名时，Pydantic 会在入口处直接拦住；
# 2. 后续如果平台集合变化，这里会成为一个清晰的单点维护位置。
SupportedPlatform = Literal["jd", "taobao", "pdd", "mock"]


class CompareRequest(BaseModel):
    """商品比价接口的请求体结构。"""

    # query 是用户输入的商品名称，FastAPI 会用这个模型自动校验请求 JSON。
    query: str = Field(..., min_length=1, description="用户输入的商品名称")

    # 文档里的 platforms 是可选字段。
    # 这里默认给空数组，表示“没有指定平台过滤条件”，
    # service 层会把它解释为“使用当前所有支持的平台”。
    platforms: list[SupportedPlatform] = Field(
        default_factory=list,
        description="指定查询平台；为空时使用当前支持的全部平台",
    )

    # 每个平台允许返回多少条候选商品。
    # 先在 schema 层限制最小值为 1，避免业务层再处理 0 或负数这种无效输入。
    max_results_per_platform: int = Field(
        default=5,
        ge=1,
        description="每个平台最多返回的候选商品数量",
    )

    # 当前阶段虽然还是 Mock 数据，但字段先和接口文档保持一致。
    # 这样前端联调时不需要等真实风险分析能力接入后再改参数名。
    enable_risk_analysis: bool = Field(
        default=True,
        description="是否启用风险分析",
    )

    # 这个字段在当前 Mock 版本里还没有真正写入价格历史，
    # 但先保留在请求模型里，保证接口输入和文档一致。
    enable_price_history: bool = Field(
        default=True,
        description="是否写入价格记录",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        """避免只有空白字符的 query 进入业务层。"""

        # 先去掉首尾空白，兼容用户传入 `"   iPhone 17 Pro   "` 这种情况。
        stripped_value = value.strip()

        # `min_length=1` 只能保证字符串长度至少为 1，
        # 但 `"   "` 这种纯空格字符串仍然会通过，所以这里要额外兜底。
        if not stripped_value:
            raise ValueError("query must not be blank")

        # 直接返回 trim 之后的值，后续业务层就不用重复 `strip()` 了。
        return stripped_value
