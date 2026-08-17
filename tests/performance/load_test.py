"""Small async smoke/load harness.

Usage:
  python tests/performance/load_test.py --base-url http://127.0.0.1:8000 --seconds 30 --concurrency 20

It intentionally uses only httpx so it can run in CI or a production-like container without a
large load-testing framework. For distributed load, use the same scenarios in k6/Gatling.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass

import httpx


@dataclass
class Sample:
    elapsed: float
    status: int


async def worker(client: httpx.AsyncClient, base_url: str, deadline: float, samples: list[Sample]) -> None:
    while time.monotonic() < deadline:
        started = time.perf_counter()
        try:
            response = await client.get(f"{base_url}/health")
            status = response.status_code
        except httpx.HTTPError:
            status = 599
        samples.append(Sample(time.perf_counter() - started, status))


async def run(base_url: str, seconds: int, concurrency: int) -> int:
    samples: list[Sample] = []
    deadline = time.monotonic() + seconds
    limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(timeout=10, limits=limits) as client:
        await asyncio.gather(*(worker(client, base_url, deadline, samples) for _ in range(concurrency)))
    latencies = [sample.elapsed for sample in samples]
    ok = sum(sample.status < 400 for sample in samples)
    report = {
        "base_url": base_url,
        "seconds": seconds,
        "concurrency": concurrency,
        "requests": len(samples),
        "successes": ok,
        "errors": len(samples) - ok,
        "rps": round(len(samples) / max(seconds, 1), 2),
        "p50_ms": round(statistics.median(latencies) * 1000, 2) if latencies else None,
        "max_ms": round(max(latencies) * 1000, 2) if latencies else None,
    }
    print(json.dumps(report, indent=2))
    return 0 if samples and ok == len(samples) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--seconds", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.base_url.rstrip("/"), max(1, args.seconds), max(1, args.concurrency))))
