from __future__ import annotations
import re
import hashlib
import math
from typing import Any, List
import requests


def norm_text(s: Any) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def to_str_or_empty(v: Any) -> str:
    if v is None:
        return ""
    try:
        # NaN
        if isinstance(v, float) and v != v:
            return ""
    except Exception:
        pass
    return str(v).strip()


def stable_hash_to_vec(text: str, dims: int) -> List[float]:
    text = text or ""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vec = []
    for i in range(dims):
        b = h[i % len(h)]
        vec.append((b / 127.5) - 1.0)
    n = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / n for v in vec]


def create_embedding(text: str) -> List[float]:  # (texts):
    """
    Simple function to call MMC embeddings API
    """

    url = "https://stg1.mmc-bedford-int-non-prod-ingress.mgti.mmc.com/coreapi/llm/embeddings/v1/mmc-tech-text-embedding-3-large"

    headers = {
        "x-api-key": "3d0e6c31-7016-4038-883b-e7f97ef4439b-12e88bc6-e92f-4d26-98c9-74f164fe51e7",
        "Content-Type": "application/json",
    }

    data = {
        "input": text,
        "user": "user-123",
        "input_type": "query",
        "encoding_format": "float",
        "model": "text-embedding-3-large",
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json() if response.status_code == 200 else response.text
    embeddings_data = sorted(result["data"], key=lambda x: x["index"])
    embeddings = [item["embedding"] for item in embeddings_data]
    return embeddings
