from __future__ import annotations

import unittest

from price_fetcher import select_price_for_item


class PriceFetcherTests(unittest.TestCase):
    def test_does_not_mix_pro_and_pro_max(self) -> None:
        blocks = [
            "iPhone 17 Pro Max 256GB simfree 未開封 確定 192,500円",
            "iPhone 17 Pro 256GB simfree 未開封 確定 178,000円",
        ]
        item = {
            "name": "iPhone 17 Pro 256GB",
            "capacity": "256GB",
            "model_keywords": ["iPhone 17 Pro", "iPhone17 Pro"],
            "exclude_keywords": ["iPhone 17 Pro Max", "iPhone17 Pro Max"],
        }

        price = select_price_for_item(blocks, item, 100000, 350000)

        self.assertEqual(price, 178000)

    def test_compact_text_still_matches(self) -> None:
        blocks = ["iPhone17ProMax512GB simfree 未開封 確定 ￥229,000"]
        item = {
            "name": "iPhone 17 Pro Max 512GB",
            "capacity": "512GB",
            "model_keywords": ["iPhone 17 Pro Max", "iPhone17 Pro Max"],
        }

        price = select_price_for_item(blocks, item, 100000, 350000)

        self.assertEqual(price, 229000)


if __name__ == "__main__":
    unittest.main()
