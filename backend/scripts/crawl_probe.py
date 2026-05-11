"""Step-by-step runner for APES Module 1 crawler.

Usage:
  python backend/scripts/crawl_probe.py --demo
  python backend/scripts/crawl_probe.py --shop hackathon-store.myshopify.com
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.services.full_store_crawler import FullStoreCrawler, build_demo_store_context


def main() -> None:
    """Parse CLI flags and run either demo or live crawler mode."""

    parser = argparse.ArgumentParser(description="Run APES Store Crawler step-by-step.")
    parser.add_argument("--shop", default="hackathon-store.myshopify.com", help="Shopify myshopify domain.")
    parser.add_argument("--demo", action="store_true", help="Use the deterministic 25-product demo context.")
    parser.add_argument("--out", default="", help="Optional JSON output path.")
    args = parser.parse_args()
    load_dotenv("backend/.env")
    if args.demo:
        context = build_demo_store_context()
        print_summary(context, [{"section": "demo", "status": "ok"}])
        write_output(args.out, context)
        return
    access_token = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN")
    storefront_token = os.getenv("SHOPIFY_STOREFRONT_ACCESS_TOKEN")
    if not access_token:
        raise SystemExit("Missing SHOPIFY_ADMIN_ACCESS_TOKEN in backend/.env")
    context, steps = asyncio.run(run_live(args.shop, access_token, storefront_token))
    print_summary(context, steps)
    write_output(args.out, context)


async def run_live(shop: str, access_token: str, storefront_token: str | None) -> tuple[dict, list[dict]]:
    """Run the live crawler and return context plus step status."""

    crawler = FullStoreCrawler(shop_url=shop, access_token=access_token, storefront_token=storefront_token)
    context = await crawler.crawl()
    return context, crawler.steps


def print_summary(context: dict, steps: list[dict]) -> None:
    """Print step-by-step crawler results without dumping secret data."""

    print("APES Store Crawler")
    print("==================")
    for step in steps:
        line = f"{step['section']}: {step['status']}"
        if step.get("reason"):
            line += f" ({step['reason']})"
        print(line)
    print()
    print(f"store_name: {context.get('store_name')}")
    print(f"store_url: {context.get('store_url')}")
    print(f"products: {len(context.get('products', []))}")
    print(f"collections: {len(context.get('collections', []))}")
    print(f"faqs: {len(context.get('faqs', []))}")
    print(f"navigation menus: {len(context.get('navigation', []))}")
    print(f"coverage: {context.get('crawl_coverage')}")
    print("policies:")
    for key, value in context.get("policies", {}).items():
        print(f"  {key}: {'present' if value else 'null'}")
    print("gaps_detected:")
    for gap in context.get("gaps_detected", []):
        print(f"  - {gap['type']}: {gap['description']} ({gap['affected_count']})")


def write_output(path: str, context: dict) -> None:
    """Write the full StoreContext JSON when an output path is provided."""

    if not path:
        return
    output_path = Path(path)
    output_path.write_text(json.dumps(context, indent=2), encoding="utf-8")
    print(f"\nwrote: {output_path}")


if __name__ == "__main__":
    main()
