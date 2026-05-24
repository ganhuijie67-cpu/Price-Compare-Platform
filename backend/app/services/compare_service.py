from typing import Any

from app.agents.compare_agent import CompareAgent
from app.schemas.compare import CompareRequest


# service 层保持很薄，只暴露稳定的业务入口。
# 具体比价流程由 CompareAgent 编排，后续替换成 LangGraph 时也更集中。
COMPARE_AGENT = CompareAgent()


def compare_products(request: CompareRequest) -> dict[str, Any]:
    """执行商品比价流程。"""

    return COMPARE_AGENT.run(request)
