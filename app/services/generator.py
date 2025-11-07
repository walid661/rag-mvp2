from typing import List, Dict
from openai import OpenAI
import re
from dotenv import load_dotenv
import os

load_dotenv()  # Charge automatiquement les variables d'environnement

class RAGGenerator:
    """Generate answers given a query and retrieved documents."""

    def __init__(self, model: str = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")):
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Budget de contexte ajustable via ENV (défaut 1800)
        self.max_context_tokens = int(os.getenv("MAX_CONTEXT_TOKENS", "1800"))

    def _pack_context(self, docs: List[Dict], max_tokens: int) -> List[Dict]:
        """Pack the highest scoring documents until the token budget is filled."""
        sorted_docs = sorted(docs, key=lambda x: x['score'], reverse=True)
        packed: List[Dict] = []
        token_count = 0
        for doc in sorted_docs:
            doc_tokens = len(doc['text'].split()) * 1.3  # rough token estimate
            if token_count + doc_tokens > max_tokens:
                break
            packed.append(doc)
            token_count += doc_tokens
        return packed

    def _build_prompt(self, query: str, context: List[Dict]) -> str:
        context_text = "\n\n".join([
            f"[Document {i+1}] {doc['payload'].get('title', '')} (ID: {doc['id']})\n" + doc['text']
            for i, doc in enumerate(context)
        ])
        return f"""You are a fitness coaching assistant. Answer the question using only the information from the context.
Always cite your sources as (Document N).

Context:
{context_text}

Question: {query}

Provide a concise, actionable answer and list relevant exercises/programs. Cite your sources."""

    def _get_system_prompt(self) -> str:
        return """You are a fitness coaching assistant. Provide advice based only on supplied documents.
Rules:
1) Never use external knowledge; only the provided context.
2) After each factual claim, cite as (Document N).
3) Use clear, professional language.
4) Avoid repeating identical attributes across bullets. Group similar items and deduplicate phrasing.
5) When listing exercises, organize by target area or equipment (e.g., glutes/quads/hamstrings; bodyweight/dumbbells). Provide concise sets/reps/rest guidance if present in context; otherwise keep it brief."""

    def generate(self, query: str, retrieved_docs: List[Dict]) -> Dict:
        context = self._pack_context(retrieved_docs, self.max_context_tokens)
        prompt = self._build_prompt(query, context)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=800
        )
        answer_text = response.choices[0].message.content
        
        # Extraire les références "(Document N)" et mapper vers le contexte
        doc_ref_re = re.compile(r"\(Document\s+(\d+)\)")
        refs = set(int(m.group(1)) for m in doc_ref_re.finditer(answer_text))
        sources = []
        for i in refs:
            if 1 <= i <= len(context):
                c = context[i-1]
                sources.append({
                    "index": i,
                    "id": c.get("id") or c.get("doc_id") or c.get("chunk_id"),
                    "source": (c.get("payload", {}).get("source") or c.get("source")),
                    "page": (c.get("payload", {}).get("page") or c.get("page")),
                    "type": (c.get("payload", {}).get("type") or c.get("payload", {}).get("domain") or c.get("type")),
                    "score": c.get("score", 0.0),
                })
        
        return {
            "answer": answer_text,
            "sources": sources,
            "context_used": context
        }