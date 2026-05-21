"""LM Studio 로컬 서버 연결 + 1회 chat completion 스모크 테스트.

사전 조건:
  1. LM Studio 를 실행하고 베이스 모델을 로드한다.
  2. "Local Server" 탭에서 "Start Server" 를 눌러 OpenAI 호환 서버를 띄운다
     (기본: http://localhost:1234/v1).
  3. `.env` 의 LMSTUDIO_* 값을 채운다.

사용법:
  uv run python scripts/smoke_test_lmstudio.py
  uv run python scripts/smoke_test_lmstudio.py --prompt "이더리움 머지 이후 ..."
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from dotenv import load_dotenv
from openai import OpenAI


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="LM Studio smoke test for invest-slm")
    parser.add_argument(
        "--prompt",
        default="삼성전자가 최근 분기 실적 발표에서 강조한 메모리 사업의 핵심 포인트를 3가지로 요약해 줘.",
    )
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.4)
    args = parser.parse_args()

    base_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    api_key = os.getenv("LMSTUDIO_API_KEY", "lm-studio")
    model = os.getenv("LMSTUDIO_MODEL", "").strip()

    if not model:
        print(
            "[!] .env 의 LMSTUDIO_MODEL 이 비어 있습니다. LM Studio 에 로드된 모델 식별자를 넣어주세요.",
            file=sys.stderr,
        )
        return 2

    print(f"[i] Endpoint: {base_url}")
    print(f"[i] Model:    {model}")

    client = OpenAI(base_url=base_url, api_key=api_key, timeout=120.0)

    messages = [
        {
            "role": "system",
            "content": (
                "당신은 한국어 투자 보조 LLM 입니다. 모든 숫자에는 시점을 명시하고, "
                "단정적 추천 대신 시나리오와 근거를 제시합니다."
            ),
        },
        {"role": "user", "content": args.prompt},
    ]

    print("[i] Generating...")
    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
    except Exception as exc:
        print(f"[!] LM Studio 호출 실패: {exc}", file=sys.stderr)
        print("    Local Server 가 실행 중이고 모델이 로드되어 있는지 확인하세요.", file=sys.stderr)
        return 1

    elapsed = time.time() - t0
    text = resp.choices[0].message.content or ""
    usage = resp.usage

    print("\n----- response -----")
    print(text)
    print("--------------------")
    if usage:
        print(
            f"[i] tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, "
            f"total={usage.total_tokens}"
        )
    print(f"[i] elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
