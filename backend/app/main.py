from fastapi import FastAPI

from app.api import routes_compare, routes_health

# FastAPI 应用对象。
# 运行 `fastapi dev app/main.py` 时，开发服务器会加载这里的 `app`。
app = FastAPI(
    title="Price Compare Platform API",
    version="0.1.0",
)

# 把健康检查路由挂到正式 API 前缀下面。
# 路由文件里写的是 `/health`，加上这个前缀后就是 `/api/v1/health`。
app.include_router(routes_health.router, prefix="/api/v1")

# 把商品比价路由挂到正式 API 前缀下面。
# 路由文件里写的是 `/compare`，加上这个前缀后就是 `/api/v1/compare`。
app.include_router(routes_compare.router, prefix="/api/v1")

# 保留一个本地开发用的短路径，方便直接访问 `/health`。
app.include_router(routes_health.router)
