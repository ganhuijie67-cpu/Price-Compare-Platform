from app.adapters.mock_platform import MockPlatformAdapter


def test_mock_platform_adapter_search_returns_mock_items() -> None:
    """确认 adapter 能正常读取本地 mock 商品。"""

    adapter = MockPlatformAdapter()

    # 不传平台过滤时，adapter 应该直接返回当前 mock 文件里的候选商品。
    items = adapter.search(platforms=[], max_results_per_platform=5)

    assert items == [
        {
            "platform": "jd",
            "title": "iPhone 17 Pro 256GB 国行",
            "price": 7999,
            "shop_name": "京东自营",
            "risk_tags": [],
        }
    ]


def test_mock_platform_adapter_search_filters_by_platform() -> None:
    """确认 adapter 会按平台过滤候选商品。"""

    adapter = MockPlatformAdapter()

    # 当前 mock 文件里只有 jd 数据。
    # 所以当平台过滤成 taobao 时，结果应该为空列表。
    items = adapter.search(platforms=["taobao"], max_results_per_platform=5)

    assert items == []
