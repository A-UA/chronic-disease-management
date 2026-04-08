from __future__ import annotations

from functools import lru_cache

import tiktoken


@lru_cache(maxsize=16)
def _get_encoding(model_name: str = "gpt-4o"):
    try:
        return tiktoken.encoding_for_model(model_name)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model_name: str = "gpt-4o") -> int:
    encoding = _get_encoding(model_name)
    return len(encoding.encode(text))
