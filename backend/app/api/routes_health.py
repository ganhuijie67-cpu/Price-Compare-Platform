from fastapi import APIRouter

# APIRouter 用来先把一组相关接口放在一起，再交给 app/main.py 统一挂载。
router = APIRouter(tags=["health"])


# 这里写的是这个路由自己的局部路径。
# 在 app/main.py 里它会被挂载两次：
# `/api/v1` + `/health` -> `/api/v1/health`
# 无前缀 + `/health` -> `/health`
@router.get("/health")
def health_check() -> dict:
    return {
        "success": True,
        "data": {
            "status": "ok",
            # 这些服务属于规划中的架构，但现在还没有真正接入。
            # 用 `not_configured` 可以避免误以为它们已经正常工作。
            "postgres": "not_configured",
            "redis": "not_configured",
            "qdrant": "not_configured",
            "version": "0.1.0",
        },
        "message": "ok",
        "request_id": "req_health",
    }
