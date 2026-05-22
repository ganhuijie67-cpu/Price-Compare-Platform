from pydantic import BaseModel, Field


class CompareRequest(BaseModel):
    """商品比价接口的请求体结构。"""

    # query 是用户输入的商品名称，FastAPI 会用这个模型自动校验请求 JSON。
    query: str = Field(..., min_length=1, description="用户输入的商品名称")
