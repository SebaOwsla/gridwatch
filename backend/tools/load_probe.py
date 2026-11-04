"""Bounded local-only concurrency probe; never targets a remote host."""

import argparse
import asyncio
import json
import math
import os
import time
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx


class PageAssets(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paths: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "script" and attributes.get("src"):
            self.paths.append(attributes["src"] or "")
        if tag == "link" and attributes.get("rel") == "stylesheet" and attributes.get("href"):
            self.paths.append(attributes["href"] or "")


def percentile(values: list[float], percentage: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[math.ceil(len(ordered) * percentage) - 1] * 1000, 2)


async def probe(
    url: str, users: int, requests_per_user: int, include_assets: bool = False,
    headers: dict[str, str] | None = None,
) -> dict:
    ready = asyncio.Event()
    latencies: list[float] = []
    statuses: Counter[str] = Counter()
    limits = httpx.Limits(max_connections=users, max_keepalive_connections=users)
    async with httpx.AsyncClient(limits=limits, timeout=10, trust_env=False, headers=headers) as client:
        assets: list[str] = []
        if include_assets:
            page = await client.get(url)
            page.raise_for_status()
            parser = PageAssets()
            parser.feed(page.text)
            assets = [urljoin(url, path) for path in parser.paths]
            if len(assets) > 10:
                raise ValueError("Page has too many assets for this bounded probe")
            if any(urlparse(asset).netloc != urlparse(url).netloc for asset in assets):
                raise ValueError("Page references a nonlocal asset")

        async def fetch(target: str) -> None:
            start = time.perf_counter()
            try:
                response = await client.get(target)
                statuses[str(response.status_code)] += 1
            except httpx.HTTPError as exc:
                statuses[type(exc).__name__] += 1
            latencies.append(time.perf_counter() - start)

        async def virtual_user() -> None:
            await ready.wait()
            for _ in range(requests_per_user):
                await fetch(url)
                if assets:
                    await asyncio.gather(*(fetch(asset) for asset in assets))

        tasks = [asyncio.create_task(virtual_user()) for _ in range(users)]
        started = time.perf_counter()
        ready.set()
        await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - started
    return {
        "url": url, "virtual_users": users, "requests_per_user": requests_per_user,
        "assets_per_page": len(assets), "total_requests": len(latencies), "elapsed_seconds": round(elapsed, 3),
        "requests_per_second": round(len(latencies) / elapsed, 1),
        "status_counts": dict(statuses),
        "latency_ms": {"p50": percentile(latencies, .50), "p95": percentile(latencies, .95),
                       "p99": percentile(latencies, .99), "max": round(max(latencies) * 1000, 2)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="100-user local GridWatch availability probe")
    parser.add_argument("url", help="Local HTTP URL, e.g. http://127.0.0.1:8000/api/v1/health/live")
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--requests-per-user", type=int, default=3)
    parser.add_argument("--page", action="store_true", help="Fetch referenced scripts and styles with each page")
    parser.add_argument("--bearer-token-env", help="Environment variable containing a local JWT")
    args = parser.parse_args()
    target = urlparse(args.url)
    if target.scheme != "http" or target.hostname not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("Only local HTTP targets are allowed")
    if not 1 <= args.users <= 100 or not 1 <= args.requests_per_user <= 5:
        parser.error("Use 1–100 users and 1–5 cycles per user")
    token = os.getenv(args.bearer_token_env) if args.bearer_token_env else None
    if args.bearer_token_env and not token:
        parser.error("The bearer token environment variable is empty")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    print(json.dumps(asyncio.run(probe(args.url, args.users, args.requests_per_user, args.page, headers)), indent=2))


if __name__ == "__main__":
    main()
