# 멀티드래곤 펀드 뉴스 워드 자동 생성기

네이버 뉴스에서 펀드별 투자자산 관련 기사를 검색해, 기사 제목을
**하이퍼링크**로 담은 워드(.docx) 파일을 자동으로 만들어 줍니다.
매주 월요일 오전, 전 주(월~일)에 나온 기사를 모아 메일 양식 그대로
정리하는 작업을 자동화합니다.

## 동작 방식

- 네이버 **공식 검색 API** 를 사용합니다. (HTML 직접 크롤링 X → 안정적이고 약관 위반 소지 없음)
- `config.json` 에 정의한 펀드 → 투자자산 → 검색 키워드 순서대로 순회합니다.
- 최신순으로 정렬해 **전 주 구간**에 발행된 기사만 골라냅니다.
- 결과를 워드 파일로 저장합니다. 각 기사 제목은 클릭하면 네이버 뉴스로 이동합니다.

## 1. 설치

```bash
pip install -r requirements.txt
```

## 2. 네이버 API 키 발급 (최초 1회)

1. https://developers.naver.com/apps 접속 → 로그인 → **애플리케이션 등록**
2. 사용 API 에서 **검색(Search)** 선택
3. 발급된 **Client ID / Client Secret** 을 환경변수로 등록

macOS / Linux:
```bash
export NAVER_CLIENT_ID="발급받은_ID"
export NAVER_CLIENT_SECRET="발급받은_SECRET"
```

Windows (PowerShell):
```powershell
setx NAVER_CLIENT_ID "발급받은_ID"
setx NAVER_CLIENT_SECRET "발급받은_SECRET"
```

> 무료 API이며 하루 25,000회까지 호출할 수 있어 본 용도에는 충분합니다.

## 3. 실행

```bash
# 전 주(월~일) 기사 수집 → 워드 생성
python main.py

# 출력 파일명 지정
python main.py --output 멀티드래곤_기사_6월3주.docx

# 기준일을 직접 지정해 그 주의 '전 주'를 수집 (테스트/재생성용)
python main.py --today 2025-06-16

# API 호출 없이 양식만 미리 보기 (더미 데이터)
python main.py --dry-run
```

기본 출력 파일명은 `멀티드래곤_기사_YYYYMMDD_YYYYMMDD.docx` 형식입니다.

## 4. 종목/펀드 수정

`config.json` 만 편집하면 됩니다. 코드 수정은 필요 없습니다.

```json
{
  "fund": "이지스 멀티드래곤 6호 펀드",
  "assets": [
    { "label": "동부건설", "keywords": ["동부건설"] },
    { "label": "큐이디-키움 시프트 신기술투자조합 (유에이치씨)", "keywords": ["유에이치씨"] }
  ]
}
```

- `label`: 워드에 표시될 자산명(조합명 + 종목명)
- `keywords`: 네이버 뉴스 검색어. 여러 개 넣으면 합쳐서 수집합니다.
  (예: 회사명 표기가 여러 가지면 `["엘디카본", "LDCarbon"]` 처럼)
- `max_articles_per_keyword`: 키워드당 최대 기사 수 (기본 5건, `config.json`의 `search`에서 조정)

## 5. 매주 월요일 자동 실행 (선택)

### Windows 작업 스케줄러
1. `작업 스케줄러` → `기본 작업 만들기`
2. 트리거: **매주 월요일 오전 8시**
3. 동작: 프로그램 시작
   - 프로그램: `python`
   - 인수: `main.py`
   - 시작 위치: 이 폴더 경로

### macOS / Linux (cron)
```bash
# crontab -e 에 추가 (매주 월요일 08:00)
0 8 * * 1 cd /경로/Claude && /usr/bin/python3 main.py >> run.log 2>&1
```

## 파일 구성

| 파일 | 설명 |
|------|------|
| `config.json`   | 펀드·투자자산·검색 키워드 설정 |
| `naver_news.py` | 네이버 검색 API 호출 및 기간 필터링 |
| `docx_writer.py`| 워드 문서 생성 (하이퍼링크 포함) |
| `main.py`       | 실행 진입점 |
