from __future__ import annotations

from dataclasses import dataclass

from price_fetcher import PriceResult


@dataclass(frozen=True)
class DecisionResult:
    decision: str
    previous_delta: int | None
    yesterday_delta: int | None
    profit: int | None
    should_notify: bool
    reason: str


def decide(
    result: PriceResult,
    cost_price: int,
    sell_target_profit: int,
    previous_price: int | None,
    yesterday_price: int | None,
    config: dict,
    notify_every_run: bool,
) -> DecisionResult:
    if result.status != "ok" or result.price is None:
        return DecisionResult(
            decision="ALERT",
            previous_delta=None,
            yesterday_delta=None,
            profit=None,
            should_notify=True,
            reason=result.message or "価格取得に失敗しました",
        )

    previous_delta = result.price - previous_price if previous_price is not None else None
    yesterday_delta = result.price - yesterday_price if yesterday_price is not None else None
    profit = result.price - cost_price

    notify_up_delta = int(config["notify_up_delta"])
    notify_down_delta = int(config["notify_down_delta"])
    wait_loss_limit = int(config.get("wait_loss_limit", -10000))

    if profit >= sell_target_profit:
        return DecisionResult(
            decision="SELL",
            previous_delta=previous_delta,
            yesterday_delta=yesterday_delta,
            profit=profit,
            should_notify=True,
            reason="売却目標に到達",
        )

    if previous_delta is not None and previous_delta >= notify_up_delta:
        return DecisionResult(
            decision="WAIT",
            previous_delta=previous_delta,
            yesterday_delta=yesterday_delta,
            profit=profit,
            should_notify=True,
            reason=f"前回比 +{previous_delta:,}円",
        )

    if previous_delta is not None and previous_delta <= notify_down_delta:
        return DecisionResult(
            decision="ALERT",
            previous_delta=previous_delta,
            yesterday_delta=yesterday_delta,
            profit=profit,
            should_notify=True,
            reason=f"前回比 {previous_delta:,}円",
        )

    if profit <= wait_loss_limit:
        decision = "WAIT"
        reason = "損益が監視ライン以下"
    else:
        decision = "WAIT"
        reason = "目標未達"

    return DecisionResult(
        decision=decision,
        previous_delta=previous_delta,
        yesterday_delta=yesterday_delta,
        profit=profit,
        should_notify=notify_every_run,
        reason=reason,
    )
