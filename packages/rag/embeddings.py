"""질의 임베딩. DB 적재 시 사용한 것과 동일한 BAAI/bge-m3(1024차원)를 써야 코사인 유사도가 의미를 가진다."""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-m3"


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_query(text: str) -> list[float]:
    return _model().encode(text, normalize_embeddings=True).tolist()
