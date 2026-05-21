# invest-slm

개인용 로컬 LLM 투자 의사결정 보조 시스템.
대상 자산: BTC/KRW, ETH/KRW (Upbit), 삼성전자(005930), SK하이닉스(000660), Alphabet(GOOGL), NVIDIA(NVDA).

전체 설계와 단계별 로드맵은 [`project.md`](./project.md) 참고.

## ⚠️ 면책

본 프로젝트는 **개인의 학습·연구 및 본인 투자 의사결정 보조**만을 목적으로 합니다.
한국 자본시장법상 불특정 다수 대상 투자자문/일임에 사용·배포하지 않습니다.
모든 출력은 정보 제공이며 매수·매도 권유가 아닙니다.

## 빠른 시작 (Phase 1)

전제: macOS Apple Silicon (M-series), Python 3.11+, [uv](https://docs.astral.sh/uv/) 설치.

```bash
# 1) 의존성 설치
uv sync

# 2) 환경 변수 파일 준비 (필요한 키만 채워도 됨)
cp .env.example .env

# 3) 모델 경로 설정
#    configs/model.yaml 의 llm.mlx.model_path 에 변환된 MLX 모델 경로를 입력
#    예: ~/models/Qwen3-30B-A3B-mlx-4bit

# 4) MLX-LM 스모크 테스트
uv run python scripts/smoke_test_mlx.py
```

## 디렉터리

```
configs/        모델·종목·리스크 규칙 설정 (YAML)
scripts/        단발성 유틸리티 (스모크 테스트, 인덱스 재빌드 등)
ingest/         (예정) 시세·공시·뉴스 수집
corpus/         (예정) 도서·논문·리포트 코퍼스
store/          (gitignored) 로컬 데이터 저장소 (DuckDB / Parquet / Chroma)
rag/            (예정) 청크·임베딩·검색
agent/          (예정) 도구 호출 에이전트
finetune/       (예정) MLX-LM LoRA SFT/DPO
eval/           (예정) 평가셋 및 채점
ui/             (예정) Gradio / Open WebUI
```

## 진행 상태

- [x] Phase 0 — 면책·범위 정의 (`project.md`)
- [x] Phase 1 — 환경 스캐폴딩 (pyproject, configs, 스모크 테스트)
- [ ] Phase 2 — 데이터 수집 파이프라인
- [ ] Phase 3 — 코퍼스 구축
- [ ] Phase 4 — RAG 인덱스
- [ ] Phase 5 — 에이전트 / 도구
- [ ] Phase 6 — (선택) 파인튜닝
- [ ] Phase 7 — 백테스팅 · 평가
- [ ] Phase 8 — UI / 운영
