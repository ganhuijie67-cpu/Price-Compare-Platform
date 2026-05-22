from fastapi import APIRouter

from app.schemas.compare import CompareRequest
from app.services.compare_service import compare_products as compare_products_service

# compare 相关接口先集中放在这个 router 里，再由 app/main.py 统一挂载。
router = APIRouter(tags=["compare"])


@router.post("/compare")
def compare_products(request: CompareRequest) -> dict:
    """接收比价请求，并把具体业务处理交给 service 层。"""

    # 路由层只负责接收请求和返回响应，不直接维护 Mock 数据。
    return compare_products_service(request.query)
