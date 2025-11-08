import os
import json
import math
import pickle
import numpy as np
from redis import Redis
from dotenv import load_dotenv

load_dotenv()

USE_REDIS_CACHE = os.getenv("USE_REDIS_CACHE", "false").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SEMANTIC_CACHE_MAX = int(os.getenv("SEMANTIC_CACHE_MAX", "200"))
SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.85"))

def _cosine(a, b):
    a, b = np.array(a), np.array(b)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))

class SemanticCache:
    def __init__(self, embed_fn):
        self.enabled = USE_REDIS_CACHE
        self.r = Redis.from_url(REDIS_URL) if self.enabled else None
        self.embed_fn = embed_fn  # callable: text -> embedding(list/np)

    def get(self, query: str):
        if not self.enabled:
            return None
        # Exact key
        key = f"sc:qa:{query.strip().lower()}"
        hit = self.r.get(key)
        if hit:
            return json.loads(hit)

        # Naive semantic scan des N derniers
        keys = self.r.lrange("sc:keys", -SEMANTIC_CACHE_MAX, -1)
        q_emb = self.embed_fn(query)
        best = (None, -1.0)
        for k in keys:
            data = self.r.get(k)
            if not data:
                continue
            obj = json.loads(data)
            e = pickle.loads(bytes.fromhex(obj["emb_hex"]))
            sim = _cosine(q_emb, e)
            if sim > best[1]:
                best = (obj, sim)
        if best[1] >= SEMANTIC_CACHE_THRESHOLD:
            return best[0]
        return None

    def set(self, query: str, answer: str, sources: list, emb):
        if not self.enabled:
            return
        key = f"sc:qa:{query.strip().lower()}"
        obj = {"q": query, "a": answer, "sources": sources, "emb_hex": pickle.dumps(emb).hex()}
        self.r.set(key, json.dumps(obj), ex=60*60*24)
        self.r.rpush("sc:keys", key)
        self.r.ltrim("sc:keys", -SEMANTIC_CACHE_MAX, -1)




