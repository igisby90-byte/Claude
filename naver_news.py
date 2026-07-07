"""네이버 뉴스 검색 모듈.

네이버 공식 검색 API(https://developers.naver.com/docs/serviceapi/search/news/news.md)를
사용해 키워드별 뉴스를 가져오고, 지정한 기간(전 주)에 해당하는 기사만 필터링한다.

HTML을 직접 크롤링하지 않고 공식 API를 쓰는 이유:
  - 페이지 구조 변경에 영향을 받지 않아 안정적이다.
  - robots.txt / 이용약관 위반 소지가 없다.
  - 발행일(pubDate), 정렬(sort=date) 등 필요한 정보를 바로 제공한다.

사전 준비:
  1. https://developers.naver.com/apps 에서 애플리케이션 등록 → "검색" API 추가
  2. 발급받은 Client ID / Client Secret 를 환경변수로 설정
       export NAVER_CLIENT_ID="발급받은_ID"
       export NAVER_CLIENT_SECRET="발급받은_SECRET"
"""

from __future__ import annotations

import html
import os
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime

import requests

NAVER_NEWS_API = "https://openapi.naver.com/v1/search/news.json"
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class Article:
    """검색된 기사 한 건."""

    title: str          # 태그/엔티티가 제거된 순수 제목
    link: str           # 클릭 시 이동할 URL (네이버 뉴스 링크 우선)
    pub_date: datetime  # 발행일시 (KST)


def _clean(text: str) -> str:
    """네이버 API가 돌려주는 제목에서 <b> 태그와 HTML 엔티티를 제거한다."""
    return html.unescape(_TAG_RE.sub("", text)).strip()


def previous_week_range(today: date | None = None) -> tuple[date, date]:
    """오늘(기본값) 기준 '전 주'의 월요일과 일요일을 반환한다.

    월요일 오전에 실행하면 직전 주(월~일) 구간을 얻는다.
    """
    today = today or date.today()
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    last_sunday = this_monday - timedelta(days=1)
    return last_monday, last_sunday


def week_of_month_label(target: date) -> str:
    """날짜를 'M월 N주' 형태의 라벨로 변환한다 (해당 월의 몇 번째 주인지)."""
    week_no = (target.day - 1) // 7 + 1
    return f"{target.month}월 {week_no}주"


def _credentials() -> tuple[str, str]:
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "네이버 API 자격증명이 없습니다. 환경변수 NAVER_CLIENT_ID / "
            "NAVER_CLIENT_SECRET 를 설정하세요.\n"
            "  https://developers.naver.com/apps 에서 발급받을 수 있습니다."
        )
    return client_id, client_secret


def search_news(
    keyword: str,
    start_date: date,
    end_date: date,
    *,
    display: int = 100,
    sort: str = "date",
    max_articles: int = 5,
    session: requests.Session | None = None,
) -> list[Article]:
    """키워드로 뉴스를 검색해 [start_date, end_date] 기간 기사만 반환한다.

    sort='date' 로 최신순 정렬 후, 기간 내 기사를 최대 max_articles 건까지 모은다.
    기간보다 오래된 기사가 나오기 시작하면 더 이상 페이지를 넘기지 않는다.
    """
    client_id, client_secret = _credentials()
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    sess = session or requests.Session()

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    collected: list[Article] = []
    seen_links: set[str] = set()

    # 네이버 API는 start 1~1000, display 최대 100. 최대 10페이지까지 순회.
    for page in range(10):
        start_index = page * display + 1
        if start_index > 1000:
            break

        params = {
            "query": keyword,
            "display": display,
            "start": start_index,
            "sort": sort,
        }
        resp = _get_with_retry(sess, headers, params)
        items = resp.json().get("items", [])
        if not items:
            break

        page_has_older = False
        for item in items:
            try:
                pub = parsedate_to_datetime(item["pubDate"])
            except (KeyError, ValueError, TypeError):
                continue
            pub_naive = pub.replace(tzinfo=None)

            if pub_naive < start_dt:
                # 최신순 정렬이므로 이후 기사는 모두 더 과거 → 페이지 순회 중단
                page_has_older = True
                continue
            if pub_naive > end_dt:
                continue

            # 네이버 뉴스 링크가 있으면 그것을, 없으면 원문 링크를 사용
            link = item.get("link") or item.get("originallink", "")
            if not link or link in seen_links:
                continue
            seen_links.add(link)

            collected.append(
                Article(title=_clean(item.get("title", "")), link=link, pub_date=pub)
            )
            if len(collected) >= max_articles:
                return collected

        if page_has_older:
            break
        time.sleep(0.3)  # API 호출 간 최소 간격 (호출 제한 회피)

    return collected


def _get_with_retry(session, headers, params, *, max_retries: int = 5):
    """네이버 API GET 호출. 429/5xx 응답 시 지수 백오프로 재시도한다.

    네이버 검색 API는 짧은 시간에 요청이 몰리면 429(Too Many Requests)를
    반환한다. 이 경우 잠시 대기 후 다시 시도하면 정상 처리된다.
    """
    delay = 2.0
    for attempt in range(max_retries):
        resp = session.get(NAVER_NEWS_API, headers=headers, params=params, timeout=10)
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt < max_retries - 1:
                wait = delay * (2 ** attempt)
                print(f"    (호출 제한 감지 → {wait:.0f}초 대기 후 재시도)")
                time.sleep(wait)
                continue
        resp.raise_for_status()
        return resp
    # 모든 재시도 실패 시 마지막 응답으로 예외 발생
    resp.raise_for_status()
    return resp
