# 아키텍처 초안 (수정)

## 1. 레이어 구성

- `models`: 표준 데이터 모델 (`DailyBar`, `CandidateScore`)
- `selectors`: 종목 탐색/선정 로직 (교체 가능)
- `strategies`: 시그널 생성 로직 (교체 가능)
- `execution`: 주문 전 검증/주문 라우팅
- `clients`: 한국투자증권 Open API 연동

## 2. 설계 원칙

1. **API 응답과 전략 로직 분리**
   - KIS 응답 포맷이 바뀌어도 전략 코드는 최대한 보호
2. **종목선정/전략 모듈의 플러그인화**
   - `StockSelector` 인터페이스를 통해 신규 로직을 쉽게 추가
3. **실거래 전 모의투자 우선**
   - 동일 전략을 모의/실거래에 공통 적용

## 3. 현재 구현된 퀀트 모듈

- `MomentumSelector`
  - 20일/60일 모멘텀 + 변동성 패널티 + 거래대금 필터
- `QuantSwingStrategy`
  - MA20/MA60 추세 기반 매수/매도
  - 손절/익절 규칙 내장
- `QuantDailyRebalanceStrategy`
  - 상위 N종목 유지 리밸런싱

## 4. 다음 구현 우선순위

1. KIS 인증/토큰 모듈
2. 일봉 조회 API -> `DailyBar` 변환 어댑터
3. 주문 요청 DTO 및 실행 모듈
4. 포지션/리스크 정책 연결
