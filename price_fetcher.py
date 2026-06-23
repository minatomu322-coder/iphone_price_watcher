from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

import requests
from bs4 import BeautifulSoup


PRICE_RE = re.compile(r"(?:¥|￥)?\s*([1-9]\d{2,3}(?:,\d{3})+|[1-9]\d{5,6})\s*円?")


@dataclass(frozen=True)
class PriceResult:
    product: str
    capacity: str
    shop: str
    price: int | None
    status: str
    message: str
    url: str


class PriceFetcher(Protocol):
    name: str

    def fetch(self, items: list[dict[str, Any]]) -> list[PriceResult]:
        """Return current prices for configured items."""


class KaikyoTsushinFetcher:
    name = "kaikyo_tsushin"

    def __init__(self, fetcher_config: dict[str, Any], scraping_config: dict[str, Any]) -> None:
        self.shop_name = fetcher_config.get("shop_name", "海峡通信")
        self.url = fetcher_config["url"]
        self.timeout = int(scraping_config.get("timeout_seconds", 20))
        self.min_price = int(scraping_config.get("min_price", 100000))
        self.max_price = int(scraping_config.get("max_price", 350000))
        self.user_agent = scraping_config.get("user_agent", "iPhonePriceWatcher/1.0")

    def fetch(self, items: list[dict[str, Any]]) -> list[PriceResult]:
        results: list[PriceResult] = []
        for url, url_items in group_items_by_url(items, self.url).items():
            results.extend(self._fetch_url_items(url, url_items))
        return results

    def _fetch_url_items(self, url: str, items: list[dict[str, Any]]) -> list[PriceResult]:
        try:
            html = self._fetch_html(url)
            blocks = extract_text_blocks(html)
            if not blocks:
                raise RuntimeError("ページ本文を取得できませんでした")
        except Exception as exc:
            return [
                PriceResult(
                    product=item["name"],
                    capacity=item["capacity"],
                    shop=self.shop_name,
                    price=None,
                    status="failed",
                    message=f"海峡通信の取得に失敗: {exc}",
                    url=url,
                )
                for item in items
            ]

        return [self._result_from_blocks(item, blocks, url) for item in items]

    def _fetch_html(self, url: str) -> str:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        }
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding
        if not response.text.strip():
            raise RuntimeError("空のレスポンスです")
        return response.text

    def _result_from_blocks(self, item: dict[str, Any], blocks: list[str], url: str) -> PriceResult:
        price = select_price_for_item(
            blocks=blocks,
            item=item,
            min_price=self.min_price,
            max_price=self.max_price,
        )
        if price is None:
            return PriceResult(
                product=item["name"],
                capacity=item["capacity"],
                shop=self.shop_name,
                price=None,
                status="failed",
                message="対象機種の価格候補が見つかりませんでした",
                url=url,
            )

        return PriceResult(
            product=item["name"],
            capacity=item["capacity"],
            shop=self.shop_name,
            price=price,
            status="ok",
            message="取得成功",
            url=url,
        )


def extract_text_blocks(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    blocks: list[str] = []
    seen: set[str] = set()
    for selector in ["tr", "li", "p", "div", "section", "article"]:
        for node in soup.select(selector):
            text = normalize_text(node.get_text(" ", strip=True))
            if len(text) < 12 or text in seen:
                continue
            seen.add(text)
            blocks.append(text)

    body = normalize_text(soup.get_text(" ", strip=True))
    if body and body not in seen:
        blocks.append(body)
    return blocks


def select_price_for_item(
    blocks: list[str],
    item: dict[str, Any],
    min_price: int,
    max_price: int,
) -> int | None:
    exact_price = select_exact_unopened_price(blocks, item, min_price, max_price)
    if exact_price is not None:
        return exact_price

    model_keywords = item.get("model_keywords", [item["name"].replace(f" {item['capacity']}", "")])
    capacity = str(item["capacity"])
    scored_prices: list[tuple[int, int]] = []

    for block in blocks:
        compact = normalize_match_text(block)
        has_model = any(normalize_match_text(keyword) in compact for keyword in model_keywords)
        has_capacity = normalize_match_text(capacity) in compact
        if not has_model or not has_capacity:
            continue

        for match in PRICE_RE.finditer(block):
            price = int(match.group(1).replace(",", ""))
            if not min_price <= price <= max_price:
                continue
            score = score_candidate(block, match.start(), item)
            scored_prices.append((score, price))

    if not scored_prices:
        return None

    scored_prices.sort(reverse=True)
    return scored_prices[0][1]


def select_exact_unopened_price(
    blocks: list[str],
    item: dict[str, Any],
    min_price: int,
    max_price: int,
) -> int | None:
    product = re.escape(str(item["name"]))
    pattern = re.compile(
        rf"{product}\s*simfree\s*未開封.*?確定\s*(?:¥|￥)?\s*([1-9]\d{{2,3}}(?:,\d{{3}})+|[1-9]\d{{5,6}})\s*円?",
        re.IGNORECASE,
    )
    for block in sorted(blocks, key=len):
        match = pattern.search(block)
        if not match:
            continue
        price = int(match.group(1).replace(",", ""))
        if min_price <= price <= max_price:
            return price
    return None


def score_candidate(block: str, price_index: int, item: dict[str, Any]) -> int:
    compact = normalize_match_text(block)
    capacity = normalize_match_text(str(item["capacity"]))
    score = 0
    if capacity in compact:
        score += 100
    for keyword in item.get("model_keywords", []):
        if normalize_match_text(keyword) in compact:
            score += 100
    for good_word in ["買取", "新品", "未開封", "未使用", "SIMフリー", "国内版"]:
        if good_word in block:
            score += 25
    for bad_word in ["中古", "ジャンク", "販売", "在庫", "ケース", "フィルム"]:
        if bad_word in block[max(0, price_index - 80) : price_index + 40]:
            score -= 120
    score -= price_index // 10
    return score


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_match_text(text: str) -> str:
    return re.sub(r"[\s　_-]+", "", text).lower()


def build_fetchers(fetcher_configs: list[dict[str, Any]], scraping_config: dict[str, Any]) -> list[PriceFetcher]:
    fetchers: list[PriceFetcher] = []
    for fetcher_config in fetcher_configs:
        if not fetcher_config.get("enabled", True):
            continue

        name = fetcher_config["name"]
        if name == KaikyoTsushinFetcher.name:
            fetchers.append(KaikyoTsushinFetcher(fetcher_config, scraping_config))
            continue

        raise ValueError(f"Unknown fetcher: {name}")

    return fetchers


def group_items_by_url(items: list[dict[str, Any]], default_url: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault(item.get("url", default_url), []).append(item)
    return grouped
