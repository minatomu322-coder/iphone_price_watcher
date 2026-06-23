from __future__ import annotations

import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from decision import DecisionResult, decide
from discord_notifier import get_webhook_url, send_discord_notification
from price_fetcher import PriceResult, build_fetchers
from storage import append_history, get_latest_price, get_price_near_yesterday


BASE_DIR = Path(__file__).resolve().parent


def load_config() -> dict[str, Any]:
    config_path = BASE_DIR / "config.yaml"
    with config_path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)


def money(value: int | None, signed: bool = False) -> str:
    if value is None:
        return "n/a"
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:,}円"


def icon_for(decision: str, profit: int | None) -> str:
    if decision == "ALERT":
        return "[ALERT]"
    if decision == "SELL":
        return "[SELL]"
    if profit is not None and profit < 0:
        return "[WAIT]"
    return "[OK]"


def build_line(result: PriceResult, decision: DecisionResult) -> str:
    return (
        f"{icon_for(decision.decision, decision.profit)} {result.product}\n"
        f"価格 {money(result.price)} / 損益 {money(decision.profit, signed=True)} / "
        f"前回 {money(decision.previous_delta, signed=True)} / 昨日 {money(decision.yesterday_delta, signed=True)}\n"
        f"判断 {decision.decision}: {decision.reason}"
    )


def run() -> int:
    config = load_config()
    items = config["items"]
    csv_path = BASE_DIR / config["storage"]["csv_path"]
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    fetchers = build_fetchers(config["fetchers"], config.get("scraping", {}))
    notify_every_run = bool(config.get("discord", {}).get("notify_every_run", True))

    lines: list[str] = []
    saved_count = 0

    for fetcher in fetchers:
        results = fetcher.fetch(items)
        results_by_product = {result.product: result for result in results}

        for item in items:
            result = results_by_product.get(
                item["name"],
                PriceResult(
                    product=item["name"],
                    capacity=item["capacity"],
                    shop=getattr(fetcher, "shop_name", fetcher.name),
                    price=None,
                    status="failed",
                    message="Fetcher did not return this item.",
                    url=getattr(fetcher, "url", ""),
                ),
            )
            previous_price = get_latest_price(csv_path, result.product, result.shop)
            yesterday_price = get_price_near_yesterday(csv_path, result.product, result.shop, now)
            decision = decide(
                result=result,
                cost_price=int(item["cost_price"]),
                sell_target_profit=int(item.get("sell_target_profit", 0)),
                previous_price=previous_price,
                yesterday_price=yesterday_price,
                config=config["decision"],
                notify_every_run=notify_every_run,
            )

            append_history(
                csv_path,
                {
                    "timestamp": timestamp,
                    "product": result.product,
                    "capacity": result.capacity,
                    "shop": result.shop,
                    "price": result.price if result.price is not None else "",
                    "cost_price": item["cost_price"],
                    "profit": decision.profit if decision.profit is not None else "",
                    "decision": decision.decision,
                    "previous_delta": decision.previous_delta if decision.previous_delta is not None else "",
                    "yesterday_delta": decision.yesterday_delta if decision.yesterday_delta is not None else "",
                    "status": result.status,
                    "message": decision.reason,
                    "url": result.url,
                },
            )
            saved_count += 1
            print(build_line(result, decision))
            if decision.should_notify:
                lines.append(build_line(result, decision))

    if lines:
        header = f"iPhone価格監視 {datetime.now().strftime('%Y-%m-%d %H:%M')} JST"
        send_discord_notification(
            webhook_url=get_webhook_url(),
            username=config["discord"]["username"],
            content=f"**{header}**\n\n" + "\n\n".join(lines),
        )
    else:
        print("No Discord notification needed.")

    return saved_count


def main() -> None:
    try:
        saved_count = run()
        print(f"saved {saved_count} rows")
    except Exception as exc:
        config = load_config()
        detail = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        send_discord_notification(
            webhook_url=get_webhook_url(),
            username=config["discord"]["username"],
            content=f"**[ALERT] iPhone価格監視でエラー**\n{detail}",
        )
        raise


if __name__ == "__main__":
    main()
