import json
from pathlib import Path
from typing import Any


# 当前文件位于 backend/app/adapters/ 下。
# `parents[3]` 回到项目根目录后，就能稳定拼出 mock 数据文件路径。
PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMPARE_MOCK_PATH = PROJECT_ROOT / "mock_data" / "platform_products" / "compare_mock.json"


class MockPlatformAdapter:
    """读取本地 Mock 商品数据，并模拟平台搜索结果。"""

    def search(
        self,
        platforms: list[str],
        max_results_per_platform: int,
    ) -> list[dict[str, Any]]:
        """按平台和每个平台上限返回候选商品。"""

        # 先把固定的 Mock 数据读进来。
        # 当前 compare 还没有接真实平台 API，所以候选商品全部来自本地 JSON。
        mock_data = self._load_compare_mock()

        # 如果请求里没有传 platforms，这里会得到空集合。
        # 后面的判断逻辑会把空集合解释成“不过滤平台”。
        platform_filter = set(platforms)

        # 记录每个平台已经保留了多少条结果。
        # 这样可以实现“每个平台最多返回 N 条”的限制。
        results_per_platform: dict[str, int] = {}
        filtered_items: list[dict[str, Any]] = []

        for item in mock_data["items"]:
            # Mock 数据里如果没写平台，默认按 mock 平台处理，
            # 这样能保证返回结果里至少有一个明确的平台值。
            platform = item.get("platform", "mock")

            # 只有在用户显式传了 platforms 时才启用平台过滤。
            # `platform_filter` 为空时，这里会直接放行全部商品。
            if platform_filter and platform not in platform_filter:
                continue

            current_count = results_per_platform.get(platform, 0)

            # 超过每个平台的上限后，继续扫描后面的商品，但不再收下当前平台的新结果。
            if current_count >= max_results_per_platform:
                continue

            # 先更新计数，再把商品加入最终返回列表。
            results_per_platform[platform] = current_count + 1
            filtered_items.append(item)

        return filtered_items

    def _load_compare_mock(self) -> dict[str, Any]:
        """从 mock_data 目录读取当前阶段使用的固定商品数据。"""

        # 明确使用 UTF-8 读取，避免中文标题在不同开发环境下出现乱码。
        with COMPARE_MOCK_PATH.open("r", encoding="utf-8") as file:
            return json.load(file)
