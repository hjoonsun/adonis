# api 를 이용한 주식 자동매매 V1.0

한국투자증권 Open API를 학습하고, Python 기반 자동매매 시스템을 단계적으로 구축하기 위한 저장소입니다.

## 1) 이번 작업에서 반영한 핵심
- API 없이 실행 가능한 **퀀트 백테스트 모듈(일봉/스윙)** 구현
- 종목 탐색/선정 로직을 **교체 가능한 구조(Selector Protocol)** 로 분리
- 종목 선정 로직 **필터/스코어 파라미터화** 적용
- 테스트 코드로 핵심 동작 검증

## 2) 실전형 백테스트 기능
- **거래 비용 반영**: 매수 수수료, 매도 수수료+세금
- **슬리피지 반영**: bps 단위로 매수/매도 체결가 조정
- **주말 거래 차단**: 주중(월~금)만 매매/평가 처리
- **CSV 리포트 출력**: `artifacts/trades.csv`, `artifacts/equity_curve.csv`

## 3) 프로젝트 구조
```text
.
├─ src/trading_bot/
│  ├─ backtesting/
│  │  ├─ engine.py
│  │  └─ report.py
│  ├─ models/market.py
│  ├─ selectors/
│  ├─ strategies/
│  └─ main.py
└─ tests/
   ├─ test_backtest_engine.py
   ├─ test_backtest_report.py
   ├─ test_quant_logic.py
   └─ test_smoke.py
```

## 4) 빠른 시작
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . --no-build-isolation
python -m trading_bot.main
pytest
```

## 5) 백테스트 모듈 설명
- `SwingBacktestEngine`
  - 입력: 종목별 일봉 데이터(universe)
  - 로직: 스윙 청산 판단 → 모멘텀 랭킹 → Top-N 리밸런싱 매수
  - 출력: 거래내역(trades), 자산곡선(equity curve), 성과지표(total return, max drawdown)
- `BacktestExecutionConfig`
  - `commission_rate`, `sell_tax_rate`, `slippage_bps`, `allow_weekend_trading`

## 6) 한국투자증권 연동 전, 먼저 할 수 있는 것
1. 유니버스 구성(코스피200/ETF)
2. 파라미터 튜닝 (`hold_top_n`, `stop_loss`, `take_profit`)
3. 체결/비용 파라미터 튜닝 (`commission_rate`, `sell_tax_rate`, `slippage_bps`)
4. 백테스트 지표 기준선 정하기 (수익률/MDD/거래횟수)

## 7) 작업 완료 후, 사용자가 해야 할 일
1. 한국투자증권 앱키/시크릿/계좌를 `.env`로 준비
2. 일봉 조회 API를 `DailyBar` 변환 함수에 연결
3. 주문 API 어댑터를 붙여 모의투자부터 실행

## 8) 종목 선정 로직 고도화 포인트
- **필터 파라미터화**: `MomentumFilterConfig`
  - `min_history`, `min_avg_turnover`, `min_price`, `max_volatility20`, `min_m20`, `min_m60`
- **스코어 파라미터화**: `MomentumScoreConfig`
  - `weight_m20`, `weight_m60`, `weight_volatility`, `weight_turnover`
- 동일 `StockSelector` 구조를 유지하므로, 추후 밸류/퀄리티 셀렉터로 교체해도 백테스트 엔진은 그대로 사용 가능
