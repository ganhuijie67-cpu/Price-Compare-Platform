from fastapi import APIRouter

from app.schemas.compare import CompareRequest
from app.services.compare_service import compare_products as compare_products_service

# compare 相关接口先集中放在这个 router 里，再由 app/main.py 统一挂载。
router = APIRouter(tags=["compare"])


@router.post("/compare")
def compare_products(request: CompareRequest) -> dict:
    """接收比价请求，并把具体业务处理交给 service 层。"""

    # 路由层只负责三件事：
    # 1. 接收并触发 FastAPI/Pydantic 的参数校验；
    # 2. 把结构化后的请求对象传给 service；
    # 3. 把 service 返回的结果原样交回给客户端。
    # 这样路由文件可以始终保持很薄，业务逻辑集中在 service 层维护。
    return compare_products_service(request)
