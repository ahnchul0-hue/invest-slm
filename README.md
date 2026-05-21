# invest-slm

개인용 로컬 LLM 투자 의사결정 보조 시스템.
대상 자산: BTC/KRW, ETH/KRW (Upbit), 삼성전자(005930), SK하이닉스(000660), Alphabet(GOOGL), NVIDIA(NVDA).

추론 백엔드: **LM Studio** (OpenAI 호환 로컬 서버).
전체 설계와 단계별 로드맵은 [`project.md`](./project.md) 참고.

## ⚠️ 면책

본 프로젝트는 **개인의 학습·연구 및 본인 투자 의사결정 보조**만을 목적으로 합니다.
한국 자본시장법상 불특정 다수 대상 투자자문/일임에 사용·배포하지 않습니다.
모든 출력은 정보 제공이며 매수·매도 권유가 아닙니다.

## 빠른 시작 (Phase 1)

전제: macOS Apple Silicon (M-series), Python 3.11+, [uv](https://docs.astral.sh/uv/), [LM Studio](https://lmstudio.ai) 설치.

```bash
# 1) 의존성 설치
uv sync

# 2) 환경 변수 파일 준비
cp .env.example .env
# .env 의 LMSTUDIO_MODEL 을 LM Studio 에 로드한 모델 식별자로 수정
```

LM Studio 준비:
1. LM Studio 실행 후 베이스 모델을 다운로드/로드한다.
   (현재 사용: `qwen3.6-35b-a3b-uncensored-hauhaucs-aggressive`)
2. 좌측 **Local Server** 탭으로 이동.
3. 상단에서 모델을 선택하고 **Start Server** 클릭.
   기본 엔드포인트는 `http://localhost:1234/v1`.
4. 서버 탭 상단에 표시되는 **모델 식별자**를 `.env` 의 `LMSTUDIO_MODEL` 에 동일하게 입력.

스모크 테스트:
```bash
uv run python scripts/smoke_test_lmstudio.py
```

응답이 정상 출력되면 Phase 1 완료.

## 디렉터리

```
configs/        모델·종목·리스크 규칙 설정 (YAML)
scripts/        단발성 유틸리티 (스모크 테스트, 인덱스 재빌드 등)
ingest/         (예정) 시세·공시·뉴스 수집
corpus/         (예정) 도서·논문·리포트 코퍼스
store/          (gitignored) 로컬 데이터 저장소 (DuckDB / Parquet / Chroma)
rag/            (예정) 청크·임베딩·검색
agent/          (예정) 도구 호출 에이전트
finetune/       (예정) LoRA SFT/DPO
eval/           (예정) 평가셋 및 채점
ui/             (예정) Gradio / Open WebUI
```

## 진행 상태

- [x] Phase 0 — 면책·범위 정의 (`project.md`)
- [x] Phase 1 — 환경 스캐폴딩 (LM Studio + configs + 스모크 테스트)
- [ ] Phase 2 — 데이터 수집 파이프라인
- [ ] Phase 3 — 코퍼스 구축
- [ ] Phase 4 — RAG 인덱스
- [ ] Phase 5 — 에이전트 / 도구
- [ ] Phase 6 — (선택) 파인튜닝
- [ ] Phase 7 — 백테스팅 · 평가
- [ ] Phase 8 — UI / 운영
