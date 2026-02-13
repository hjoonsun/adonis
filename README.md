# api 를 이용한 주식 자동매매 V1.0

한국투자증권 Open API를 학습하고, Python 기반 자동매매 시스템을 단계적으로 구축하기 위한 저장소입니다.

## 1) 이번 작업에서 반영한 핵심
- API 없이 실행 가능한 **퀀트 백테스트 모듈(일봉/스윙)** 구현
- 종목 탐색/선정 로직을 **교체 가능한 구조(Selector Protocol)** 로 분리
- 종목 선정 로직 **필터/스코어 파라미터화** 적용
- 테스트 코드로 핵심 동작 검증

## 2) 실전형 백테스트 기능
- **스윙 전략 세분화**: 진입 버퍼, 모멘텀 확인, 쿨다운, 트레일링 스탑, 최대 보유일 적용
- **거래 비용 반영**: 매수 수수료, 매도 수수료+세금
- **슬리피지 반영**: bps 단위로 매수/매도 체결가 조정
- **주말 거래 차단**: 주중(월~금)만 매매/평가 처리
- **CSV 리포트 출력**: `artifacts/trades.csv`, `artifacts/equity_curve.csv`, `artifacts/batch_summary.csv`
- **RiskManager 적용**: 최대 보유종목 수/종목당 비중/일중 손실 제한
- **성과지표 확장**: CAGR, Sharpe, Win Rate, Profit Factor
- **배치 검증 자동화**: bull/sideways/bear/volatile 시나리오 일괄 실행 + summary CSV

## 3) 프로젝트 구조
```text
.
├─ src/trading_bot/
│  ├─ backtesting/
│  │  ├─ engine.py
│  │  └─ report.py
│  ├─ models/market.py
│  ├─ clients/kis_auth.py
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
  - 로직: 스윙 청산 판단 → 모멘텀 랭킹 → Top-N 리밸런싱 매수 + RiskManager 검증
  - 출력: 거래내역(trades), 자산곡선(equity curve), 성과지표(total return, CAGR, max drawdown, Sharpe, win rate, profit factor)
- `BacktestExecutionConfig`
  - `commission_rate`, `sell_tax_rate`, `slippage_bps`, `allow_weekend_trading`

## 6) 한국투자증권 연동 전, 먼저 할 수 있는 것
1. 유니버스 구성(코스피200/ETF)
2. 파라미터 튜닝 (`hold_top_n`, `stop_loss`, `take_profit`, `trailing_stop`, `max_holding_days`)
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

## 9) KIS 인증 모듈(키 없이 구현 가능한 범위)
- `KISAuthConfig.from_env()`로 환경변수 검증/로드 (`KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_BASE_URL`, `KIS_IS_PAPER`)
- `KISAuthClient.get_access_token()`은 토큰 캐시를 우선 사용하고, 만료/강제갱신 시 재발급 함수(`fetch_token`)를 호출
- 네트워크 호출은 의존성 주입(`fetch_token`)으로 분리되어 Mock 테스트 가능


## 10) .env 템플릿 분리(모의/실전)
- 모의투자: `.env.paper.example`
- 실전투자: `.env.live.example`
- 빠른 시작/호환용: `.env.example`

사용 예시:
```bash
cp .env.paper.example .env
# 또는
cp .env.live.example .env
```

## 11) 보안상 `.env` 관리 방법
- 실제 키가 들어간 `.env`는 **절대 커밋하지 않기** (`.gitignore`에 이미 `.env` 포함).
- 저장소에는 예시 파일(`.env*.example`)만 버전관리.
- 키 유출이 의심되면 즉시 한국투자증권에서 앱키/시크릿 재발급(회전).
- 팀 협업 시 키는 Git이 아닌 비밀관리 수단(예: 1Password, Vault, GitHub Actions Secrets)으로 공유.
