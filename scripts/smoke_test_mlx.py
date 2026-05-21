"""MLX-LM 로딩 + 1회 generate 스모크 테스트.

실행 환경: Apple Silicon (M-series) macOS.
사용법:
    uv run python scripts/smoke_test_mlx.py
    # 또는 모델 경로를 명시
    uv run python scripts/smoke_test_mlx.py --model ~/models/Qwen3-30B-A3B-mlx-4bit
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import yaml


def load_model_path(default_cfg: Path) -> str:
    if not default_cfg.exists():
        return ""
    cfg = yaml.safe_load(default_cfg.read_text())
    return (cfg.get("llm", {}).get("mlx", {}).get("model_path") or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="MLX-LM smoke test for invest-slm")
    parser.add_argument(
        "--model",
        default=None,
        help="MLX 모델 경로. 미지정 시 configs/model.yaml 의 llm.mlx.model_path 사용.",
    )
    parser.add_argument(
        "--prompt",
        default="삼성전자가 최근 분기 실적 발표에서 강조한 메모리 사업의 핵심 포인트를 3가지로 요약해 줘.",
    )
    parser.add_argument("--max-tokens", type=int, default=256)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    model_path = args.model or load_model_path(repo_root / "configs" / "model.yaml")
    if not model_path:
        print(
            "[!] 모델 경로가 비어 있습니다. configs/model.yaml 의 llm.mlx.model_path 를 채우거나 "
            "--model 로 전달하세요.",
            file=sys.stderr,
        )
        return 2

    try:
        from mlx_lm import generate, load
    except ImportError:
        print(
            "[!] mlx-lm 이 설치되어 있지 않습니다. Apple Silicon Mac 에서 `uv sync` 후 실행하세요.",
            file=sys.stderr,
        )
        return 3

    print(f"[i] Loading model from: {model_path}")
    t0 = time.time()
    model, tokenizer = load(model_path)
    print(f"[i] Loaded in {time.time() - t0:.1f}s")

    messages = [
        {
            "role": "system",
            "content": (
                "당신은 한국어 투자 보조 LLM입니다. 모든 숫자에는 시점을 명시하고, "
                "단정적 추천 대신 시나리오와 근거를 제시합니다."
            ),
        },
        {"role": "user", "content": args.prompt},
    ]
    prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)

    print("[i] Generating...")
    t1 = time.time()
    text = generate(model, tokenizer, prompt=prompt, max_tokens=args.max_tokens, verbose=False)
    elapsed = time.time() - t1
    print("\n----- response -----")
    print(text)
    print("--------------------")
    print(f"[i] {args.max_tokens} max-tokens in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
