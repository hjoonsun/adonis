# 모의 데이터 기반 테스트 결과 보고서

- 생성 시각(UTC): 2026-02-13 04:42:20
- 주의: 본 결과는 실시간/실거래 데이터가 아닌 **임의(Mock) 데이터** 기반입니다.

## 1) 실행한 명령
```bash
pytest
python -m trading_bot.main
```

## 2) 테스트 요약
- `pytest`: **21 passed**
- 단일 데모 백테스트 요약:
```text
api 를 이용한 주식 자동매매 V1.0 - 실전형 백테스트 데모
trades=54
total_return=0.03%
max_drawdown=-2.48%
cagr=0.09%, sharpe=0.05
win_rate=11.11%, profit_factor=1.58
csv=artifacts/trades.csv, artifacts/equity_curve.csv
batch_scenarios=4, batch_csv=artifacts/batch_summary.csv
```

## 3) 배치 시나리오 결과 (`artifacts/batch_summary.csv`)

| scenario | total_return | cagr | max_drawdown | sharpe | win_rate | profit_factor | trades |
|---|---:|---:|---:|---:|---:|---:|---:|
| bull | 21.15% | 52.25% | -1.01% | 5.59 | 100.00% | 0.00 | 7 |
| sideways | -23.17% | -43.88% | -23.12% | -8.80 | 0.00% | 0.00 | 86 |
| bear | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | 0.00 | 0 |
| volatile | 5.49% | 12.42% | -1.36% | 1.58 | 100.00% | 0.00 | 5 |

## 4) 산출물 파일
- `artifacts/trades.csv`
- `artifacts/equity_curve.csv`
- `artifacts/batch_summary.csv`
- `docs/mock-backtest-report.md` (본 문서)