# Local Investment Advisor LLM (invest-slm)

> 개인용 로컬 LLM 기반 투자 의사결정 보조 시스템
> 대상 자산: BTC/KRW, ETH/KRW (Upbit), 삼성전자(005930), SK하이닉스(000660), Alphabet(GOOGL), NVIDIA(NVDA)

---

## 0. 면책 / 법적 고지

- 본 프로젝트는 **개인의 학습·연구 및 본인 투자 의사결정 보조**만을 목적으로 한다.
- 한국 자본시장법상 **불특정 다수 대상 투자자문/일임/유사투자자문업**은 인가·등록 대상이며, 본 시스템을 그러한 용도로 사용·배포하지 않는다.
- 모든 출력은 정보 제공이며 매수·매도 권유가 아니다. 손익 책임은 사용자에게 있다.
- 학습/색인에 사용하는 모든 자료는 **본인 소장 또는 라이선스가 명확한 공개 자료**만 사용한다 (저작권 준수).

---

## 1. 목표

1. 6개 종목에 대해 **시세·공시·뉴스·거시지표를 종합한 일일 브리핑** 생성
2. 자연어 질의에 대해 **근거 문서를 인용한 답변(RAG)** 제공
3. 사용자가 정의한 **리스크 규칙(MDD, 포지션 한도 등)** 을 강제하는 가드레일
4. **로컬 추론**으로 외부 송신 없이 동작 (시세/뉴스 API 호출 제외)

비목표(Non-goals)
- 자동매매 주문 집행 (Phase 2 이후 별도 검토)
- 모든 종목·전 자산군 커버
- 초단타/HFT

---

## 2. 하드웨어 & 추론 스택

- **Mac M5 Max / 128GB Unified Memory**
- 베이스 모델: `qwen3.6-35b-a3b-uncensored-hauhaucs-aggressive`
  (Qwen3 계열 MoE, 총 ~35B / active ~3B 추정 → 메모리 여유 충분)
- 추론 백엔드(우선순위)
  1. **MLX-LM** (Apple Silicon 네이티브, LoRA 파인튜닝까지 가능)
  2. **llama.cpp** (GGUF Q4_K_M / Q5_K_M, Ollama 또는 LM Studio 경유)
  3. (옵션) **vLLM**은 Mac에서 미지원 → 사용 안 함
- 양자화 권장: MLX 4bit 또는 GGUF Q5_K_M
- 임베딩 모델: `BAAI/bge-m3` (다국어) 또는 `intfloat/multilingual-e5-large`
- 리랭커: `BAAI/bge-reranker-v2-m3`
- 벡터 DB: **Qdrant**(로컬 도커) 또는 **Chroma**(파일 기반, 초기 권장)

---

## 3. 디렉터리 구조 (예정)

```
invest-slm/
├── project.md                # 본 문서
├── README.md
├── pyproject.toml            # uv 기반
├── .env.example
├── configs/
│   ├── tickers.yaml          # 6개 종목 메타
│   ├── risk_rules.yaml       # 개인 리스크 규칙
│   └── model.yaml            # 모델/임베딩 경로
├── ingest/                   # 데이터 수집
│   ├── upbit.py              # BTC/ETH 시세·체결
│   ├── krx.py                # pykrx / FDR
│   ├── us_equity.py          # yfinance / Alpha Vantage
│   ├── dart.py               # 한국 전자공시
│   ├── edgar.py              # 미국 SEC 공시
│   ├── news_rss.py           # 한경/매경/Reuters/Bloomberg RSS
│   └── macro.py              # FRED / ECOS
├── corpus/                   # 학습·색인용 텍스트 코퍼스
│   ├── books/                # 본인 소장 PDF/EPUB
│   ├── reports/              # 증권사·국책연구원 공개 리포트
│   ├── papers/               # arXiv q-fin
│   └── filings/              # DART/EDGAR 원문
├── store/                    # 가공 결과
│   ├── prices.duckdb
│   ├── news.parquet
│   └── chunks/
├── rag/
│   ├── chunk.py
│   ├── embed.py
│   ├── index.py              # Qdrant/Chroma
│   └── retriever.py          # BM25 + dense 하이브리드
├── agent/
│   ├── tools.py              # function calling 스키마
│   ├── prompts/
│   └── runner.py
├── finetune/                 # (Phase 6에서 활성화)
│   ├── sft_data.jsonl
│   ├── dpo_data.jsonl
│   └── train_mlx.py
├── eval/
│   ├── qa_set.jsonl
│   └── grade.py
├── ui/
│   └── app_gradio.py
└── scripts/
    ├── daily_brief.py        # cron 진입점
    └── refresh_index.py
```

---

## 4. 단계별 로드맵

### Phase 1 — 환경 구축 (1~2일)
- [ ] `uv init` + Python 3.12 환경
- [ ] MLX-LM 설치, 베이스 모델 로딩 테스트 (`mlx_lm.generate`)
- [ ] Ollama 또는 LM Studio로 GGUF 양자화 모델 백업 준비
- [ ] 임베딩 모델(`bge-m3`) 다운로드 및 인코딩 속도 측정
- [ ] Chroma 로컬 인스턴스 기동 확인

### Phase 2 — 데이터 수집 파이프라인 (3~5일)
종목별로 최소 5년치 일봉 + 최근 2년치 분봉(가능 범위) + 공시·뉴스 적재.

| 자산 | 일/분봉 | 공시 | 뉴스 | 거시 |
|---|---|---|---|---|
| BTC/KRW, ETH/KRW | Upbit REST/WS | — | CoinDesk RSS, 코인데스크코리아 | Glassnode 무료, CoinGecko |
| 005930, 000660 | pykrx, FDR | DART OpenAPI | 네이버금융, 한경, 매경 RSS | 한국은행 ECOS |
| GOOGL, NVDA | yfinance, Alpha Vantage | SEC EDGAR (10-K/10-Q/8-K) | Reuters/Bloomberg/Yahoo RSS, GDELT | FRED |

- [ ] 저장 포맷: 시세는 **DuckDB**, 뉴스·공시 원문은 **Parquet + 원본 파일**
- [ ] 키 관리: `.env` (Upbit API Key, DART API Key, FRED API Key, Alpha Vantage Key)
- [ ] 증분 업데이트 + 중복 제거(URL/hash) 구현
- [ ] cron / `launchd`로 매일 06:30 KST 갱신

### Phase 3 — 코퍼스 구축 (1~2주, 점진적)
**도서 (본인 소장본만)**
- 《현명한 투자자》(그레이엄), 《전설로 떠나는 월가의 영웅》(피터 린치), 《주식시장을 이기는 작은 책》(그린블라트), 《돈, 뜻밖의 진실》(모건 하우절), 워런 버핏 주주서한(공식 PDF, 공개)
- 한국: 《한국형 가치투자 전략》, 《재무제표 모르면 주식투자 절대로 하지마라》 등 (저작권상 RAG 인덱싱만, 외부 공유 금지)
- 가상화폐: 《비트코인 백서》(공개), 《이더리움 백서》(공개), 《Mastering Bitcoin》(저자 무료 공개), 《Mastering Ethereum》(무료 공개)

**공개 보고서/데이터**
- 자본시장연구원(KCMI), 한국금융연구원(KIF), KIEP, KDI
- 한국거래소 「KRX Market」, 「상장공시시스템」 통계
- 증권사 무료 공개 산업/기업 분석 리포트(한경 컨센서스, 와이즈리포트)
- 미국: Fed FOMC 의사록, BLS, BEA, 각사 IR 프레젠테이션

**논문**
- arXiv `q-fin.*`, SSRN 공개분
- HuggingFace 데이터셋
  - `ChanceFocus/FLUPE`, `ChanceFocus/PIXIU` (금융 멀티태스크)
  - `AdaptLLM/finance-tasks`
  - `FinGPT/fingpt-sentiment-train`
  - `gtfintechlab/finer-ord`
  - 한국어: `klue`, `KorFin-ASC`, `kowiki-text`

**가공 규칙**
- 모두 **Markdown으로 정규화** (`pandoc`, `pymupdf`, `unstructured`)
- 각 청크에 `{source, license, published_at, ticker?, lang}` 메타데이터 필수
- 라이선스가 모호한 자료는 `corpus/_quarantine/`에 격리, 인덱싱 제외

### Phase 4 — RAG 인덱스 (3~5일)
- [ ] 청크 전략: 800~1,200 토큰, 15% overlap, 표/숫자는 별도 청크
- [ ] 임베딩: `bge-m3` (한·영·코드 동시 처리)
- [ ] 하이브리드 검색: BM25(`rank_bm25` 또는 Qdrant sparse) + dense + 리랭커
- [ ] 메타데이터 필터(예: `ticker=005930 AND date>=2024-01-01`) 강제
- [ ] **시세 RAG 분리**: 숫자 시계열은 임베딩보다 SQL/DuckDB로 직접 조회 → 답변 단계에서 도구 호출

### Phase 5 — 에이전트 & 도구 (1~2주)
function-calling 스키마(JSON) 예시:

```yaml
tools:
  - get_price_history(ticker, start, end, interval)
  - get_technical_indicators(ticker, indicators=[RSI,MACD,BB])
  - get_orderbook_snapshot(ticker)          # 업비트
  - get_recent_filings(ticker, n=5)         # DART/EDGAR
  - search_news(query, ticker?, days=7)
  - get_macro_series(code, start, end)      # FRED/ECOS
  - run_backtest(rule_dsl, ticker, period)
  - check_risk_rules(portfolio)
```

- 프롬프트: ReAct + 한국어 시스템 프롬프트, 답변에는 반드시 **출처(파일/URL)** 와 **숫자의 시점** 명시
- 가드레일: "매수/매도 추천 단정 금지 → 시나리오 + 근거 + 리스크" 형식 강제

### Phase 6 — (선택) 파인튜닝 (2~4주)
필요성: RAG로 80%를 처리하고, 그래도 부족한 한국어 금융 어휘·요약 스타일을 강화하고 싶을 때만.

- **MLX-LM LoRA SFT**
  - 데이터: 위 코퍼스로부터 `(질문, 근거, 답변)` 삼중쌍 자동 합성 + 수동 보정 1,000~3,000개
  - 형식: ChatML, 시스템 프롬프트 고정
- **DPO**
  - 동일 질문에 대해 "근거 인용 O / X" 두 답변 쌍을 만들고 인용 있는 쪽을 선호로
- 메모리: 35B-A3B MoE는 4bit LoRA가 128GB에서 여유 (배치 1, ctx 4k 기준)
- 산출물: `finetune/adapters/inv-v1/`

### Phase 7 — 백테스팅 & 평가 (1주)
- **퀀트 백테스트**: `vectorbt` 또는 `backtrader` — LLM이 제시한 규칙을 DSL로 받아 검증
- **LLM-as-Judge**: 50~100문항 평가셋(`eval/qa_set.jsonl`)
  - 정답 인용 일치율, 환각률, 숫자 정확도(시점 포함), 한국어 자연도
- **회귀 테스트**: 모델/인덱스 교체 시 점수 비교

### Phase 8 — UI & 운영 (3~5일)
- Open WebUI 또는 Gradio 기반 채팅 UI
- 메인 화면: 6개 종목 카드(현재가, 1D/1W/1M, 주요 뉴스 3건, AI 코멘트)
- "오늘의 브리핑" 자동 생성 (06:50 KST, Markdown 리포트 → `daily/2026-05-21.md`)
- 알림: 사용자 정의 임계치 돌파 시 macOS 알림 (`terminal-notifier`)

---

## 5. 일정 (현실적 추정)

| 주차 | 작업 |
|---|---|
| W1 | Phase 1, 2 (환경 + Upbit/KRX/yfinance 인제스트) |
| W2 | Phase 2 마무리(DART/EDGAR/뉴스), Phase 3 코퍼스 정리 시작 |
| W3 | Phase 3 코퍼스, Phase 4 RAG 인덱스 v1 |
| W4 | Phase 5 도구·에이전트, 평가셋 작성 시작 |
| W5 | Phase 7 평가 v1, Phase 8 UI 프로토타입 |
| W6+ | (선택) Phase 6 파인튜닝, 운영 자동화 |

---

## 6. 리스크 및 운영 원칙

- **데이터 신선도**: 시세·뉴스는 항상 호출 시점 기준 재조회, 임베딩 캐시에 의존 금지
- **시간대**: 모든 타임스탬프 ISO 8601 + UTC 저장, 표시만 KST 변환
- **재현성**: 모델/임베딩/인덱스 버전을 답변 메타데이터에 기록
- **개인정보·키**: `.env`만 사용, 깃 커밋 금지 (`.gitignore` 강제)
- **모델 한계**: 미래 예측 단정 금지, 확률·시나리오 표현 사용
- **저작권**: 외부 공개 시에는 인용 출처와 라이선스 표기, 도서 본문 장기 인용 금지

---

## 7. 데이터셋·자료 출처 요약 표

| 카테고리 | 출처 | 무료 | API | 비고 |
|---|---|---|---|---|
| 암호화폐 시세 | Upbit Open API | ✅ | REST/WS | KRW 마켓 직접 조회 |
| 암호화폐 온체인 | Glassnode Studio | 일부 | ✅ | 무료 티어 제한적 |
| 암호화폐 가격(보조) | CoinGecko | ✅ | REST | 키 불필요 |
| 한국 주식 시세 | pykrx, FinanceDataReader | ✅ | 파이썬 | KRX 크롤링 |
| 한국 공시 | DART OpenAPI (opendart.fss.or.kr) | ✅ | REST | 키 발급 필요 |
| 미국 주식 시세 | yfinance, Alpha Vantage | ✅ | 파이썬/REST | AV는 분당 호출 제한 |
| 미국 공시 | SEC EDGAR | ✅ | REST/RSS | User-Agent 필수 |
| 미 거시 | FRED (StLouis Fed) | ✅ | REST | 키 필요 |
| 한 거시 | 한국은행 ECOS | ✅ | REST | 키 필요 |
| 뉴스 | 네이버금융, 한경/매경 RSS | ✅ | RSS | robots.txt 준수 |
| 글로벌 뉴스 | Reuters/Bloomberg RSS, GDELT 2.0 | ✅ | RSS/BQ | GDELT는 BigQuery 무료층 |
| 논문 | arXiv q-fin | ✅ | REST | 메타 + PDF |
| 금융 데이터셋 | HuggingFace: PIXIU, FinGPT, FinanceBench, financial-phrasebank, KorFin-ASC, KLUE | ✅ | HF Hub | 라이선스 개별 확인 |
| 도서 | 본인 소장본 (PDF/EPUB), 공개 백서 | — | — | 외부 공유 금지 |

---

## 8. 첫 주 체크리스트 (바로 실행 가능)

- [ ] `uv venv && uv add mlx-lm transformers sentence-transformers chromadb duckdb pykrx finance-datareader yfinance feedparser python-dotenv tenacity httpx`
- [ ] `configs/tickers.yaml` 작성 (6종목 메타)
- [ ] `ingest/upbit.py`: 최근 5년 일봉·1년 1분봉 다운로드 → DuckDB
- [ ] `ingest/krx.py`, `ingest/us_equity.py`: 동일 작업
- [ ] `corpus/papers/`에 arXiv q-fin 최신 100편 다운로드 스크립트
- [ ] `rag/embed.py` + `rag/index.py`로 Chroma 인덱스 v0 생성
- [ ] MLX-LM으로 베이스 모델 + RAG 컨텍스트 묶어 "삼성전자 최근 분기 실적 요약" 질문 한 번 통과시키기

---

## 9. 참고 (공식·신뢰 가능 링크 위주)

- Upbit Open API 문서
- DART OpenAPI (https://opendart.fss.or.kr)
- SEC EDGAR (https://www.sec.gov/edgar/sec-api-documentation)
- FRED API (https://fred.stlouisfed.org/docs/api/fred/)
- 한국은행 ECOS (https://ecos.bok.or.kr/api/)
- HuggingFace Datasets — `PIXIU`, `FinGPT`, `FinanceBench`
- MLX-LM (https://github.com/ml-explore/mlx-examples)
- llama.cpp / Ollama

---

_End of project.md_
