from app.agents.compare_agent import CompareAgent
from app.schemas.compare import CompareRequest


def test_compare_agent_runs_compare_flow() -> None:
    agent = CompareAgent()
    request = CompareRequest(
        query="iPhone 17 Pro 256GB 国行",
        platforms=["jd", "taobao", "pdd"],
        max_results_per_platform=5,
        enable_risk_analysis=True,
        enable_price_history=True,
    )

    result = agent.run(request)

    assert result["success"] is True
    assert result["message"] == "ok"
    assert result["request_id"].startswith("req_")

    data = result["data"]
    assert data["query_id"].startswith("cq_")
    assert data["normalized_product"] == {
        "brand": "Apple",
        "name": "iPhone 17 Pro",
        "model": "iPhone 17 Pro",
        "capacity": "256GB",
        "version": "国行",
        "color": None,
    }
    assert data["summary"]["lowest_price"] == 7499
    assert data["summary"]["lowest_platform"] == "pdd"
    assert data["summary"]["recommended_platform"] == "jd"
    assert data["summary"]["result_count"] == 6
    assert "pdd 当前价格最低" in data["buying_advice"]
    assert "jd 在匹配度和风险上更稳" in data["buying_advice"]


def test_compare_agent_can_disable_risk_analysis() -> None:
    agent = CompareAgent()
    request = CompareRequest(
        query="iPhone 17 Pro 256GB 国行",
        platforms=["pdd"],
        enable_risk_analysis=False,
    )

    result = agent.run(request)
    items = result["data"]["items"]

    assert len(items) == 2
    assert {item["platform"] for item in items} == {"pdd"}
    assert all(item["risk_tags"] == [] for item in items)
    assert all(item["risk_level"] is None for item in items)
