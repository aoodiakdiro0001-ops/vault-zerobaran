#!/usr/bin/env python3
"""
Vault-ZeroBaran — CLI: Ask a question from the terminal.

Usage:
    python scripts/query_cli.py "ما هي سياسة الإرجاع؟"
    python scripts/query_cli.py --top-k 8 "البند المالي في العقد"
    python scripts/query_cli.py --raw "..."
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loguru import logger

from config.settings import settings
from core.utils import banner
from core.rag_engine import ask, format_answer_for_chat


def main() -> int:
    p = argparse.ArgumentParser(description="Vault-ZeroBaran — Query CLI")
    p.add_argument("question", help="Your question (in any language).")
    p.add_argument("--top-k", type=int, default=None,
                   help=f"Number of chunks to retrieve (default: {settings.vault_top_k}).")
    p.add_argument("--raw", action="store_true",
                   help="Print the raw JSON result instead of the chat-formatted text.")
    args = p.parse_args()

    print(banner())
    logger.info(f"Asking Vault-ZeroBaran: '{args.question}'")

    result = ask(args.question, top_k=args.top_k)

    if args.raw:
        print(json.dumps({
            "answer":   result.answer,
            "sources":  result.sources,
            "backend":  result.backend,
            "owner":    settings.ownership_block(),
        }, ensure_ascii=False, indent=2))
    else:
        print()
        print(format_answer_for_chat(result))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
