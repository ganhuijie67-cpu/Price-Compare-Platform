from app.tools.product_parse import ProductParseTool


def test_parse_iphone_17_pro_256gb_china_version() -> None:
    parser = ProductParseTool()

    result = parser.parse("iPhone 17 Pro 256GB 国行")

    assert result == {
        "brand": "Apple",
        "model": "iPhone 17 Pro",
        "capacity": "256GB",
        "version": "国行",
        "category": "phone",
    }


def test_parse_unknown_product_keeps_empty_fields() -> None:
    parser = ProductParseTool()

    result = parser.parse("未知商品")

    assert result == {
        "brand": None,
        "model": None,
        "capacity": None,
        "version": None,
        "category": None,
    }
