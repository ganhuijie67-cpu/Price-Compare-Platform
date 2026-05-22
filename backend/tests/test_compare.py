from fastapi.testclient import TestClient

from app.main import app


# TestClient 会在内存里调用 FastAPI 应用，所以测试时不需要真的启动服务器。
client = TestClient(app)


def test_compare_returns_mock_items() -> None:
    # 这是第一个业务接口：输入商品名称，后端先返回固定 Mock 商品。
    response = client.post(
        "/api/v1/compare",
        json={"query": "iPhone 17 Pro 256GB 国行"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "iPhone 17 Pro 256GB 国行",
        "normalized_product": {
            "brand": "Apple",
            "model": "iPhone 17 Pro",
            "capacity": "256GB",
            "version": "国行",
            "category": "phone",
        },
        "items": [
            {
                "platform": "jd",
                "title": "iPhone 17 Pro 256GB 国行",
                "price": 7999,
                "shop_name": "京东自营",
                "risk_tags": [],
                "match_score": 0.95,
                "match_reasons": ["型号一致", "容量一致", "版本一致"],
                "is_match": True,
            }
        ],
    }


def test_compare_requires_query() -> None:
    # 如果请求体里没有 query，Pydantic 会让 FastAPI 自动返回 422 校验错误。
    response = client.post("/api/v1/compare", json={})

    assert response.status_code == 422
