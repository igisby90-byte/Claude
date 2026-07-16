#!/usr/bin/env python3
"""FRED에서 DFII10(10년 TIPS 실질금리)을 받아 data/dfii10.csv를 월말 기준으로 갱신.

로컬 PC처럼 fred.stlouisfed.org 접근이 되는 환경에서 실행하세요.
(Claude Code 원격 컨테이너에서는 네트워크 정책상 차단될 수 있음)

사용법:  python scripts/fetch_dfii10.py
"""
import csv
import io
import urllib.request
from pathlib import Path

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10&cosd=2024-01-01"
OUT = Path(__file__).resolve().parent.parent / "data" / "dfii10.csv"


def main():
    req = urllib.request.Request(FRED_URL, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=30).read().decode()
    rows = list(csv.reader(io.StringIO(raw)))[1:]  # skip header

    # 월별 마지막 관측치만 남긴다
    monthly = {}
    for date, val in rows:
        if val in (".", ""):
            continue
        monthly[date[:7]] = val  # 같은 달이면 뒤(더 늦은 날짜)가 덮어씀

    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "dfii10", "status"])
        for month in sorted(monthly):
            w.writerow([month, monthly[month], "actual"])
    print(f"updated {OUT} ({len(monthly)} months, latest {max(monthly)}={monthly[max(monthly)]})")


if __name__ == "__main__":
    main()
