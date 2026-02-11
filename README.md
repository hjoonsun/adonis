# api 를 이용한 주식 자동매매 V1.0

한국투자증권 Open API를 학습하고, Python 기반 자동매매 시스템을 단계적으로 구축하기 위한 저장소입니다.

## 1) 이번 작업에서 반영한 핵심
- 종목 탐색/선정 로직을 **교체 가능한 구조(Selector Protocol)** 로 분리
- 첫 전략으로 **퀀트(일봉/스윙)** 로직 구현
- 일봉 기준 리밸런싱(Top-N)과 스윙(추세/손절/익절) 의사결정 제공
- 테스트 코드로 핵심 동작 검증

## 2) 권장 개발 순서 (수정안)
기존 순서를 아래처럼 조정하는 것을 권장합니다.

1. **데이터 표준화 레이어 먼저 구현**
   - 한국투자증권 API 응답을 내부 `DailyBar` 모델로 변환
2. **종목 선정 로직 플러그인 구조 확정**
   - `StockSelector` 인터페이스를 기준으로 로직 교체 가능하게 유지
3. **전략 엔진(퀀트) 구현**
   - `QuantSwingStrategy`, `QuantDailyRebalanceStrategy`부터 운영
4. **주문/리스크 연결**
   - 선정/시그널 결과를 주문 모듈로 연결
5. **실거래 전 모의투자 검증**
   - 백테스트 + 모의투자 결과가 기준치 만족 시 실거래 전환

> 이유: 종목선정/전략은 자주 바뀌므로 API 세부 호출보다 먼저 "교체 가능한 코어"를 잡는 편이 유지보수에 유리합니다.

## 3) 프로젝트 구조
```text
.
├─ docs/
│  ├─ architecture.md
│  └─ prompt-guide.md
├─ src/
│  └─ trading_bot/
│     ├─ models/
│     │  └─ market.py
│     ├─ selectors/
│     │  ├─ base.py
│     │  └─ quant_momentum.py
│     ├─ strategies/
│     │  └─ quant_swing.py
│     └─ main.py
├─ tests/
│  ├─ test_quant_logic.py
│  └─ test_smoke.py
├─ pytest.ini
└─ setup.py
```

## 4) 빠른 시작
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . --no-build-isolation
python -m trading_bot.main
pytest
```

## 5) 퀀트 전략(1일/스윙) 요약

### A. 종목 선정: MomentumSelector
- 20일/60일 수익률 + 20일 변동성 패널티 + 20일 평균 거래대금 필터
- 점수 상위 종목만 다음 단계로 전달

### B. 스윙 시그널: QuantSwingStrategy
- 진입: `MA20 > MA60` 이고 현재가가 MA20 위
- 청산: 추세 이탈(`MA20 < MA60`) 또는 손절/익절 기준 도달

### C. 일봉 리밸런싱: QuantDailyRebalanceStrategy
- 랭킹 상위 N개만 보유하도록 매일 재조정

## 6) 한국투자증권 Open API 학습 관련 메모
- 본 실행 환경에서는 외부 GitHub 접속이 제한되어 원문 저장소를 직접 동기화하지 못했습니다.
- 대신 현 단계에서는 "API 응답을 내부 표준 모델로 변환 후 전략/주문 모듈과 분리" 원칙을 우선 적용했습니다.
- 네트워크가 허용되는 로컬 환경에서 `open-trading-api` 예제를 확인해 endpoint/헤더/토큰 정책을 즉시 연결하면 됩니다.

## 7) 작업 완료 후, 사용자가 해야 할 일
1. 한국투자증권 앱키/시크릿/계좌를 `.env`로 준비
2. Open API 예제 기준으로 **일봉 조회 API** 를 `DailyBar` 변환 함수에 연결
3. 관심 유니버스(코스피200/ETF 등) 정의
4. 전략 파라미터(`stop_loss`, `take_profit`, `hold_top_n`)를 본인 성향에 맞게 조정
5. 모의투자 계정으로 최소 2주 이상 시뮬레이션 후 실거래 전환

필요하면 다음 턴에서 바로
- KIS 인증/토큰 모듈
- 일봉 데이터 수집 클라이언트
- 주문 실행 어댑터
까지 이어서 구현하겠습니다.
