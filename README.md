# api 를 이용한 주식 자동매매 V1.0

한국투자증권 Open API를 학습하고, Python 기반 자동매매 시스템을 단계적으로 구축하기 위한 저장소 초기 세팅입니다.

## 1) 프로젝트 목표
- 한국투자증권 Open API 인증/호출 흐름 이해
- 시세 조회/주문/잔고 기능을 모듈화하여 자동매매 기반 마련
- 백테스트와 실거래 코드를 분리해 안전한 운영 구조 확보
- VS Code + 로컬 개발 + GitHub 협업에 최적화된 개발 환경 구성

## 2) 권장 개발 방식 (GitHub + 로컬 VS Code)
가장 안정적인 흐름은 **로컬에서 VS Code로 개발하고 GitHub로 동기화**하는 방식입니다.

1. GitHub에 원격 저장소 생성
2. 로컬에서 이 프로젝트를 clone
3. `.env` 파일에 API 키/계좌 정보 저장 (`.env.example` 참고)
4. 기능 단위 브랜치(`feature/...`)에서 개발
5. PR 기반 리뷰/병합

> 이유: API 키 보안 관리가 쉽고, 디버깅/테스트 속도가 빠르며, 커밋 이력 관리가 명확합니다.

## 3) 현재 초기 구조
```text
.
├─ docs/
│  ├─ architecture.md
│  └─ prompt-guide.md
├─ src/
│  └─ trading_bot/
│     ├─ __init__.py
│     └─ main.py
├─ tests/
│  └─ test_smoke.py
├─ .env.example
├─ .gitignore
├─ pyproject.toml
└─ README.md
```

## 4) 빠른 시작
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m trading_bot.main
pytest
```

## 5) 다음 단계 (우선순위)
1. 인증 토큰 발급/갱신 모듈 구현
2. 시세 조회 모듈 구현
3. 주문 실행 모듈 구현 (모의투자 우선)
4. 전략 인터페이스/리스크 관리 모듈 구현
5. 백테스트 환경 연동

## 6) 역할 정의 (프로젝트 전문가 모드)
이 저장소는 다음 범위를 일괄 수행하는 것을 전제로 구성합니다.
- 아키텍처 설계
- 주요 로직 설계/구현
- 테스트 코드 작성
- 실행/검증 자동화

필요 시 `docs/prompt-guide.md`의 템플릿을 사용해 프롬프트를 구체화하며 진행합니다.
