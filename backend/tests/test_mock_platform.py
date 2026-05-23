from app.adapters.mock_platform import MockPlatformAdapter


def test_mock_platform_adapter_search_returns_mock_items() -> None:
    """确认 adapter 能正常读取本地 mock 商品。"""

    adapter = MockPlatformAdapter()

    # 不传平台过滤时，adapter 应该直接返回当前 mock 文件里的候选商品。
    items = adapter.search(platforms=[], max_results_per_platform=5)

    assert len(items) == 6
    assert [item["platform"] for item in items] == [
        "jd",
        "jd",
        "taobao",
        "taobao",
        "pdd",
        "pdd",
    ]
    assert items[0]["platform_product_id"] == "jd_100001"
    assert items[-1]["platform_product_id"] == "pdd_300002"


def test_mock_platform_adapter_search_filters_by_platform() -> None:
    """确认 adapter 会按平台过滤候选商品。"""

    adapter = MockPlatformAdapter()

    # 当前 mock 文件里有多个平台。
    # 当平台过滤成 taobao 时，结果应该只包含淘宝候选商品。
    items = adapter.search(platforms=["taobao"], max_results_per_platform=5)

    assert len(items) == 2
    assert {item["platform"] for item in items} == {"taobao"}


def test_mock_platform_adapter_search_limits_results_per_platform() -> None:
    """确认 adapter 会限制每个平台的返回数量。"""

    adapter = MockPlatformAdapter()

    # 每个平台限制 1 条时，jd / taobao / pdd 应该各返回 1 条。
    items = adapter.search(
        platforms=["jd", "taobao", "pdd"],
        max_results_per_platform=1,
    )

    assert len(items) == 3
    assert [item["platform"] for item in items] == ["jd", "taobao", "pdd"]
