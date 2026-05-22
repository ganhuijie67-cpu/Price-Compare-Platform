import re
from typing import Any


class ProductParseTool:
    """商品名称解析工具的最小版本。"""

    def parse(self, query: str) -> dict[str, Any]:
        """把用户输入的商品名称解析成后端更容易处理的结构。"""

        normalized_query = query.strip()

        return {
            "brand": self._parse_brand(normalized_query),
            "model": self._parse_model(normalized_query),
            "capacity": self._parse_capacity(normalized_query),
            "version": self._parse_version(normalized_query),
            "category": self._parse_category(normalized_query),
        }

    def _parse_brand(self, query: str) -> str | None:
        # 当前先只识别 iPhone，后续再扩展小米、华为、荣耀等品牌。
        if "iphone" in query.lower():
            return "Apple"
        return None

    def _parse_model(self, query: str) -> str | None:
        # 识别类似 `iPhone 17 Pro`、`iPhone 17 Pro Max` 的型号。
        match = re.search(r"iphone\s+\d+(?:\s+[a-z]+)*", query, re.IGNORECASE)
        if not match:
            return None

        words = match.group(0).split()
        return " ".join(word.capitalize() if word.islower() else word for word in words)

    def _parse_capacity(self, query: str) -> str | None:
        # 识别 128GB、256GB、1TB 这类容量字段。
        match = re.search(r"\b\d+\s*(?:gb|tb)\b", query, re.IGNORECASE)
        if not match:
            return None

        return match.group(0).replace(" ", "").upper()

    def _parse_version(self, query: str) -> str | None:
        # 当前先识别国行，后续可以继续补充港版、美版、日版等版本。
        if "国行" in query:
            return "国行"
        return None

    def _parse_category(self, query: str) -> str | None:
        # 当前只要识别到 iPhone，就先归类为手机。
        if "iphone" in query.lower():
            return "phone"
        return None
