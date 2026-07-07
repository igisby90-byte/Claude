"""네이버 뉴스를 크롤링해 펀드 투자자산 기사 워드 파일을 자동 생성한다.

사용 예:
    # 기본: 전 주(월~일) 기사 수집 → 워드 생성
    python main.py

    # 출력 경로 지정
    python main.py --output 보고서.docx

    # 기준일을 직접 지정(테스트용). 해당 일자의 '전 주'를 수집
    python main.py --today 2025-06-16

    # API 호출 없이 더미 데이터로 양식만 확인
    python main.py --dry-run
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

import naver_news as nn
from docx_writer import build_document


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def collect(config: dict, start_date: date, end_date: date) -> dict:
    """설정의 모든 펀드/자산/키워드를 순회하며 기사를 수집한다."""
    search_cfg = config.get("search", {})
    results: dict = {}

    import requests
    session = requests.Session()

    for fund_cfg in config["funds"]:
        fund_name = fund_cfg["fund"]
        results[fund_name] = {}
        for asset in fund_cfg["assets"]:
            label = asset["label"]
            articles = []
            seen = set()
            for keyword in asset["keywords"]:
                found = nn.search_news(
                    keyword,
                    start_date,
                    end_date,
                    display=search_cfg.get("naver_display", 100),
                    sort=search_cfg.get("sort", "date"),
                    max_articles=search_cfg.get("max_articles_per_keyword", 5),
                    session=session,
                )
                for art in found:
                    if art.link not in seen:
                        seen.add(art.link)
                        articles.append(art)
            articles.sort(key=lambda a: a.pub_date, reverse=True)
            results[fund_name][label] = articles
            print(f"  · {fund_name} / {label}: {len(articles)}건")
            import time
            time.sleep(0.3)  # 자산 간 간격 (API 호출 제한 회피)
    return results


def make_dummy_results(config: dict, start_date: date) -> dict:
    """--dry-run 용 더미 데이터 (API 미호출, 양식 확인 목적)."""
    from datetime import timedelta

    results: dict = {}
    for fund_cfg in config["funds"]:
        fund_name = fund_cfg["fund"]
        results[fund_name] = {}
        for asset in fund_cfg["assets"]:
            label = asset["label"]
            kw = asset["keywords"][0]
            results[fund_name][label] = [
                nn.Article(
                    title=f"[예시] {kw} 관련 샘플 기사 제목입니다",
                    link="https://news.naver.com/",
                    pub_date=datetime.combine(
                        start_date + timedelta(days=2), datetime.min.time()
                    ),
                )
            ]
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="네이버 뉴스 → 펀드 기사 워드 생성기")
    parser.add_argument("--config", default="config.json", help="설정 파일 경로")
    parser.add_argument("--output", default=None, help="출력 .docx 경로")
    parser.add_argument("--today", default=None, help="기준일 YYYY-MM-DD (전 주 계산용)")
    parser.add_argument("--dry-run", action="store_true", help="API 미호출, 더미 데이터로 양식 확인")
    args = parser.parse_args()

    config = load_config(args.config)

    today = (
        datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else date.today()
    )
    start_date, end_date = nn.previous_week_range(today)
    week_label = nn.week_of_month_label(start_date)

    print(f"기준일: {today} → 수집 기간: {start_date} ~ {end_date} ({week_label})")

    if args.dry_run:
        print("[dry-run] 네이버 API 를 호출하지 않고 더미 데이터로 생성합니다.")
        results = make_dummy_results(config, start_date)
    else:
        print("네이버 뉴스 검색 중...")
        results = collect(config, start_date, end_date)

    doc = build_document(config, results, week_label, start_date, end_date)

    output = args.output or f"멀티드래곤_기사_{start_date:%Y%m%d}_{end_date:%Y%m%d}.docx"
    doc.save(output)
    print(f"\n완료: {Path(output).resolve()}")


if __name__ == "__main__":
    main()
