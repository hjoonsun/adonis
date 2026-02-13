# 아키텍처 초안 (백테스트 우선)

## 1. 레이어 구성
- `models`: 표준 데이터 모델 (`DailyBar`, `CandidateScore`)
- `selectors`: 종목 탐색/선정 로직
- `strategies`: 시그널 생성 로직
- `backtesting`: API 없이 실행 가능한 시뮬레이션 엔진
- `clients/execution`: KIS 연동 단계에서 추가 연결

## 2. 현재 구현
1. `MomentumSelector` (종목 랭킹, 필터/스코어 파라미터화)
   - `MomentumFilterConfig`, `MomentumScoreConfig`로 규칙/가중치 분리
2. `QuantSwingStrategy` (진입/청산 세분화)
   - 진입 버퍼, 모멘텀 확인, 쿨다운, 트레일링 스탑, 최대 보유일
3. `QuantDailyRebalanceStrategy` (Top-N 보유)
4. `SwingBacktestEngine` (거래/자산곡선/성과지표 산출)
5. `BacktestExecutionConfig` (수수료/세금/슬리피지/주말거래 허용 설정)
6. `RiskManager` (최대 보유 수/비중/일일 손실 제한)
7. 확장 성과지표 (CAGR, Sharpe, Win Rate, Profit Factor)
8. CSV 리포트 (`trades.csv`, `equity_curve.csv`)
9. 배치 시나리오 자동검증 (`batch_summary.csv`)

## 3. 다음 단계
1. KIS 인증/토큰 모듈
2. 일봉 조회 API -> `DailyBar` 변환 어댑터
3. 주문 API 어댑터 + 리스크 정책 연결
