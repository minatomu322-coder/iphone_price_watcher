# iPhone Price Watcher

GitHub Actionsで毎時実行し、海峡通信のiPhone買取価格をDiscordへ通知する監視システムです。

常時起動PCは不要です。GitHub Actions上で動き、履歴は `data/iphone_prices.csv` に保存されます。

## 監視対象

- iPhone 17 Pro 256GB
- iPhone 17 Pro 512GB
- iPhone 17 Pro Max 256GB
- iPhone 17 Pro Max 512GB

## 通知内容

Discord通知だけで判断できるよう、各機種ごとに以下を表示します。

- 現在の買取価格
- 今売った場合の利益または損
- 前回比
- 昨日比
- SELL / WAIT / ALERT

## GitHub Secrets

GitHubリポジトリで以下を設定してください。

1. `Settings`
2. `Secrets and variables`
3. `Actions`
4. `New repository secret`
5. `DISCORD_WEBHOOK_URL` を追加

値にはDiscordのWebhook URLを入れます。

## GitHub Actions

`.github/workflows/iphone-watch.yml` が以下に対応しています。

- `workflow_dispatch`: 手動実行
- `schedule`: 毎時実行
- `data/iphone_prices.csv` の自動コミット

スケジュールはUTC基準で毎時0分です。

## 初回確認手順

1. このディレクトリをGitHubへpush
2. GitHub Secretsに `DISCORD_WEBHOOK_URL` を設定
3. Actionsタブで `iPhone Price Watch` を開く
4. `Run workflow` で手動実行
5. Discordに通知が届くことを確認
6. `data/iphone_prices.csv` に履歴が追加されることを確認

## ローカル実行

```bash
pip install -r requirements.txt
python main.py
```

Webhook未設定時はDiscord送信せず、通知内容を標準出力に表示します。

## 設定

原価や取得URLは `config.yaml` で管理します。

`cost_price` は利益計算に使う購入価格です。実際の購入額と違う場合はここだけ直してください。
