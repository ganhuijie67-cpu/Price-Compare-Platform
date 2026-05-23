from app.tools.compare_rank import CompareRankTool


UPDATED_AT = "2026-05-21T10:30:00+08:00"


def test_build_summary_uses_coupon_price_for_lowest_price() -> None:
    rank_tool = CompareRankTool()

    summary = rank_tool.build_summary(
        [
            {
                "platform": "jd",
                "price": 7999,
                "coupon_price": None,
                "match_score": 0.95,
                "risk_level": "low",
            },
            {
                "platform": "pdd",
                "price": 7599,
                "coupon_price": 7499,
                "match_score": 0.95,
                "risk_level": "high",
            },
        ],
        UPDATED_AT,
    )

    assert summary == {
        "lowest_price": 7499,
        "lowest_platform": "pdd",
        "recommended_platform": "jd",
        "result_count": 2,
        "updated_at": UPDATED_AT,
    }


def test_build_summary_recommends_higher_match_score_first() -> None:
    rank_tool = CompareRankTool()

    summary = rank_tool.build_summary(
        [
            {
                "platform": "jd",
                "price": 7999,
                "match_score": 0.8,
                "risk_level": "low",
            },
            {
                "platform": "taobao",
                "price": 7699,
                "match_score": 0.95,
                "risk_level": "medium",
            },
        ],
        UPDATED_AT,
    )

    assert summary["lowest_platform"] == "taobao"
    assert summary["recommended_platform"] == "taobao"


def test_build_summary_uses_risk_level_when_match_score_ties() -> None:
    rank_tool = CompareRankTool()

    summary = rank_tool.build_summary(
        [
            {
                "platform": "taobao",
                "price": 7799,
                "match_score": 0.95,
                "risk_level": "medium",
            },
            {
                "platform": "jd",
                "price": 7999,
                "match_score": 0.95,
                "risk_level": "low",
            },
        ],
        UPDATED_AT,
    )

    assert summary["lowest_platform"] == "taobao"
    assert summary["recommended_platform"] == "jd"


def test_build_summary_returns_empty_summary_for_no_items() -> None:
    rank_tool = CompareRankTool()

    summary = rank_tool.build_summary([], UPDATED_AT)

    assert summary == {
        "lowest_price": None,
        "lowest_platform": None,
        "recommended_platform": None,
        "result_count": 0,
        "updated_at": UPDATED_AT,
    }
