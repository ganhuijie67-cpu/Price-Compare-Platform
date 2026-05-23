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
    assert body["data"]["summary"]["lowest_price"] == 7499
    assert body["data"]["summary"]["lowest_platform"] == "pdd"
    assert body["data"]["summary"]["recommended_platform"] == "jd"
    assert body["data"]["summary"]["result_count"] == 6
    assert len(body["data"]["agent_trace"]) == 3
    assert "pdd 当前价格最低" in body["data"]["buying_advice"]
    assert "jd 在匹配度和风险上更稳" in body["data"]["buying_advice"]

    items = body["data"]["items"]
    assert [item["platform"] for item in items] == [
        "jd",
        "jd",
        "taobao",
        "taobao",
        "pdd",
        "pdd",
    ]
    assert [item["platform_product_id"] for item in items] == [
        "jd_100001",
        "jd_100002",
        "tb_200001",
        "tb_200002",
        "pdd_300001",
        "pdd_300002",
    ]
    assert items[0] == {
        "platform": "jd",
        "platform_product_id": "jd_100001",
        "title": "Apple iPhone 17 Pro 256GB 国行 全网通",
        "price": 7999,
        "coupon_price": None,
        "currency": "CNY",
        "shop_name": "Apple 产品京东自营旗舰店",
        "shop_type": "self_operated",
        "product_url": "https://example.com/jd/100001",
        "image_url": "https://example.com/jd/100001.jpg",
        "match_score": 0.95,
        "risk_tags": [],
        "risk_level": "low",
        "recommendation_reason": "型号一致，容量一致，版本一致，匹配度较高，风险较低",
        "updated_at": body["data"]["summary"]["updated_at"],
    }
    assert items[4]["platform"] == "pdd"
    assert items[4]["coupon_price"] == 7499
    assert items[4]["risk_level"] == "high"


def test_compare_requires_query() -> None:
    # 如果请求体里没有 query，Pydantic 会让 FastAPI 自动返回 422 校验错误。
    response = client.post("/api/v1/compare", json={})

    assert response.status_code == 422
