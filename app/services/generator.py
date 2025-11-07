from typing import List, Dict
from openai import OpenAI
import re
from dotenv import load_dotenv
import os
import tiktoken

load_dotenv()  # Charge automatiquement les variables d'environnement

class RAGGenerator:
    """Generate answers given a query and retrieved documents."""

    def __init__(self, model: str = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")):
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Budget de contexte et plafond de docs (ENV) — valeurs plus frugales par défaut
        self.max_context_tokens = int(os.getenv("MAX_CONTEXT_TOKENS", "1000"))
        self.max_docs = int(os.getenv("MAX_DOCS", "5"))
        # Contrôle fin de la génération
        self.max_output_tokens = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "220"))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        # Encodage token pour un comptage précis
        self._enc = tiktoken.get_encoding("cl100k_base")

    def _pack_context(self, docs: List[Dict], max_tokens: int) -> List[Dict]:
        """Pack the highest scoring documents until the token budget is filled."""
        sorted_docs = sorted(docs, key=lambda x: x['score'], reverse=True)
        packed: List[Dict] = []
        token_count = 0
        for doc in sorted_docs[:self.max_docs]:
            # Comptage exact des tokens pour contrôler le budget
            doc_tokens = len(self._enc.encode(doc['text']))
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
        return """You are a fitness coaching assistant. Answer ONLY from the provided documents.
Rules:
1) Never use external knowledge; only the provided context.
2) After each factual claim, cite as (Document N).
3) Be concise: no preamble or titles; start directly with bullets. 4–6 bullets max, no redundant wording.
4) Respect user constraints ONLY if they are explicitly present. Never assume 'no equipment' unless the user states it. If the user specifies equipment (e.g., dumbbells), include such items.
5) Merge similar headings; no duplicate sections. Group related items under one heading.
6) When listing exercises, organize by target area or equipment (e.g., glutes/quads/hamstrings; bodyweight/dumbbells).
7) If sets/reps/rest exist in the context, include them briefly; otherwise omit."""

    def generate(self, query: str, retrieved_docs: List[Dict]) -> Dict:
        context = self._pack_context(retrieved_docs, self.max_context_tokens)
        prompt = self._build_prompt(query, context)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_output_tokens
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