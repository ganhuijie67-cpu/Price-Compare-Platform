from app.tools.product_match import ProductMatchTool


PARSED_PRODUCT = {
    "model": "iPhone 17 Pro",
    "capacity": "256GB",
    "version": "国行",
}


def test_match_same_product() -> None:
    matcher = ProductMatchTool()

    result = matcher.match_item(
        PARSED_PRODUCT,
        {"title": "iPhone 17 Pro 256GB 国行", "platform": "jd"},
    )

    assert result["match_score"] == 0.95
    assert result["match_reasons"] == ["型号一致", "容量一致", "版本一致"]
    assert result["is_match"] is True


def test_accessory_is_not_match() -> None:
    matcher = ProductMatchTool()

    result = matcher.match_item(
        PARSED_PRODUCT,
        {"title": "iPhone 17 Pro 手机壳 防摔保护套", "platform": "taobao"},
    )

    assert result["match_score"] == 0.0
    assert result["match_reasons"] == ["配件商品，不是主商品"]
    assert result["is_match"] is False


def test_used_product_lowers_score_but_keeps_reasons() -> None:
    matcher = ProductMatchTool()

    result = matcher.match_item(
        PARSED_PRODUCT,
        {"title": "二手 iPhone 17 Pro 256GB 国行 99新", "platform": "pdd"},
    )

    assert result["match_score"] == 0.75
    assert result["match_reasons"] == [
        "型号一致",
        "容量一致",
        "版本一致",
        "成色或来源需要确认",
    ]
    assert result["is_match"] is True


def test_missing_capacity_is_lower_score() -> None:
    matcher = ProductMatchTool()

    result = matcher.match_item(
        PARSED_PRODUCT,
        {"title": "iPhone 17 Pro 国行", "platform": "jd"},
    )

    assert result["match_score"] == 0.7
    assert result["match_reasons"] == ["型号一致", "版本一致"]
    assert result["is_match"] is True
