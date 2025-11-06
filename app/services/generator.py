from typing import List, Dict
import openai
from dotenv import load_dotenv
import os

load_dotenv()  # Charge automatiquement les variables d'environnement
openai.api_key = os.getenv("OPENAI_API_KEY")

class RAGGenerator:
    """Generate answers given a query and retrieved documents."""

    def __init__(self, model: str = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")):
        self.model = model
        # Reserve room for the output; adjust according to model context window.
        self.max_context_tokens = 6000

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
        return """You are a fitness coaching assistant. Your task is to provide exercise and training program advice based only on supplied documents. Follow these rules:
1. Never make assumptions or use external knowledge.
2. Cite sources in the form (Document N) after each factual claim.
3. Use clear, professional language.
"""

    def generate(self, query: str, retrieved_docs: List[Dict]) -> Dict:
        context = self._pack_context(retrieved_docs, self.max_context_tokens)
        prompt = self._build_prompt(query, context)
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=800
        )
        answer_text = response.choices[0].message.content
        return {
            "answer": answer_text,
            "context_used": context
        }