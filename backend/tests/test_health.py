from fastapi.testclient import TestClient

from app.main import app


# TestClient 会在内存里调用 FastAPI 应用，所以测试时不需要真的启动服务器。
client = TestClient(app)


def test_api_v1_health() -> None:
    # 这是给前端使用的正式版本化 API 路径。
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {
            "status": "ok",
            "postgres": "not_configured",
            "redis": "not_configured",
            "qdrant": "not_configured",
            "version": "0.1.0",
        },
        "message": "ok",
        "request_id": "req_health",
    }


def test_root_health_alias() -> None:
    # 这是本地开发时方便访问的短路径。
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"
