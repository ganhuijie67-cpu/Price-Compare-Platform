from fastapi.testclient import TestClient

from app.main import app


# TestClient 会在内存里调用 FastAPI 应用，所以测试时不需要真的启动服务器。
client = TestClient(app)


def test_compare_returns_mock_items() -> None:
    # 这是第一个业务接口：输入商品名称，后端先返回固定 Mock 商品。
    response = client.post(
        "/api/v1/compare",
        json={
            "query": "iPhone 17 Pro 256GB 国行",
            "platforms": ["jd", "taobao", "pdd"],
            "max_results_per_platform": 5,
            "enable_risk_analysis": True,
            "enable_price_history": True,
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["success"] is True
    assert body["message"] == "ok"
    assert body["request_id"].startswith("req_")

    assert body["data"]["query_id"].startswith("cq_")
    assert body["data"]["normalized_product"] == {
        "brand": "Apple",
        "name": "iPhone 17 Pro",
        "model": "iPhone 17 Pro",
        "capacity": "256GB",
        "version": "国行",
        "color": None,
    }
    assert body["data"]["summary"]["lowest_price"] == 7999
    assert body["data"]["summary"]["lowest_platform"] == "jd"
    assert body["data"]["summary"]["recommended_platform"] == "jd"
    assert body["data"]["summary"]["result_count"] == 1
    assert len(body["data"]["agent_trace"]) == 3
    assert "jd 当前价格和匹配度都更优" in body["data"]["buying_advice"]

    assert body["data"]["items"] == [
        {
            "platform": "jd",
            "platform_product_id": "jd_mock_001",
            "title": "iPhone 17 Pro 256GB 国行",
            "price": 7999,
            "coupon_price": None,
            "currency": "CNY",
            "shop_name": "京东自营",
            "shop_type": "self_operated",
            "product_url": None,
            "image_url": None,
            "match_score": 0.95,
            "risk_tags": [],
            "risk_level": "low",
            "recommendation_reason": "型号一致，容量一致，版本一致，匹配度较高，风险较低",
            "updated_at": body["data"]["summary"]["updated_at"],
        }
    ]


def test_compare_requires_query() -> None:
    # 如果请求体里没有 query，Pydantic 会让 FastAPI 自动返回 422 校验错误。
    response = client.post("/api/v1/compare", json={})

    assert response.status_code == 422
