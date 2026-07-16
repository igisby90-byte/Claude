# 메모리 착시 트래커

명목 capex vs 실질 구매량 — **DFII10 실질금리 · 빅테크 4사(MSFT/GOOGL/META/AMZN) capex · 서버 DRAM 계약가**를
한 곳에서 추적해 "메모리 값이 얼마나 오르고, 실제 구매량(비트)은 얼마나 늘고 있는지"를 관찰합니다.

## 구성

```
data/capex.csv       ← 4사 분기 capex ($B)          — 실적 발표 때마다 수동 업데이트
data/dram.csv        ← 서버 DRAM 계약가 QoQ (%)      — TrendForce 발표 때마다 수동 업데이트
data/dfii10.csv      ← DFII10 월말 (%)               — fetch 스크립트 또는 수동
data/params.csv      ← 메모리·부품 비중 가정 등 파라미터
scripts/build.py     ← CSV → tracker.xlsx + dashboard.html 동시 생성
scripts/fetch_dfii10.py ← FRED에서 DFII10 자동 수집 (로컬 PC용)
scripts/template.html   ← 대시보드 템플릿 (데이터는 build.py가 주입)
tracker.xlsx         ← 생성물: 엑셀 (수식 + 네이티브 차트 5개)
dashboard.html       ← 생성물: 브라우저에서 바로 여는 대시보드
```

## 업데이트 루틴 (틈날 때마다)

1. `data/*.csv`에 새 수치 입력 (또는 로컬에서 `python scripts/fetch_dfii10.py`)
2. `pip install openpyxl` (최초 1회) 후 `python scripts/build.py`
3. `dashboard.html`(브라우저)과 `tracker.xlsx`(엑셀)가 함께 재생성됨

엑셀에서는 **Params!B2(메모리·부품 비중 %)** 셀만 바꾸면 Derived 시트와 차트가 재계산됩니다.
HTML에서는 상단 슬라이더로 같은 가정을 실시간 조정할 수 있습니다.

## 핵심 지표 정의

| 지표 | 계산 | 의미 |
|---|---|---|
| DRAM 계약가 지수 | QoQ 상승률 누적 (2025Q1=100) | 메모리 "물가" |
| 명목 메모리 지출 | 총 capex × 비중 가정(기본 13%) | 가격표 합계 |
| 실질 구매량 지수 | 명목 지출 ÷ 가격지수 | 비트 프록시 — "사과 개수" |
| 실질 총 capex | 비메모리 + 메모리/(지수/100) | 메모리 물가만 디플레이트 |
| 착시 폭 (%p) | 명목 YoY − 실질 YoY | 물가가 만든 성장률 |

## 데이터 상태 플래그

- `actual` — 발표치 / `actual~` — 발표치 근사 (리스 포함 기준 등 차이 가능, 검증 권장)
- `estimate` / `forecast` — 가이던스 배분 추정, TrendForce 전망 → **실제치로 교체 필요**
- `fill_me` — 빈 칸 (DFII10 2026-02 이후)

주요 앵커: MSFT FY26 capex $190B 중 메모리·부품 $25B(13.2%, Amy Hood CFO) ·
TrendForce 서버 DRAM QoQ 1Q26 +93~98% → 2Q26 +58~63%(전망) → 3Q26 +13~18%(전망, 2026-07-09).

## 한계 (해석 시 주의)

- 13% 비중의 4사 일괄 적용은 거친 가정 — 회사별 메모리 노출도가 다름 (슬라이더/Params로 조정)
- LTA(장기공급계약)·가격 하한 때문에 실지불가는 TrendForce 계약가 지수와 괴리될 수 있음 (착시 폭 상·하단 모두 과장 가능)
- 비트 프록시는 서버당 탑재량 증가를, GPU $/FLOP 하락(역방향 디플레이터)은 반영하지 않음
