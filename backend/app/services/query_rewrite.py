from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class PreparedRetrievalQuery:
    original_query: str
    normalized_query: str
    retrieval_query: str


def normalize_query(query: str) -> str:
    normalized = query.strip().replace("？", "?").replace("，", ",").replace("：", ":")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def rewrite_query(normalized_query: str) -> str:
    rewrites = {
        "这个药还要继续吃吗": "用药是否需要继续",
        "这个药还能继续吃吗": "用药是否需要继续",
    }
    return rewrites.get(normalized_query, normalized_query)


def prepare_retrieval_query(query: str) -> PreparedRetrievalQuery:
    normalized_query = normalize_query(query)
    retrieval_query = rewrite_query(normalized_query)
    return PreparedRetrievalQuery(
        original_query=query,
        normalized_query=normalized_query,
        retrieval_query=retrieval_query,
    )
