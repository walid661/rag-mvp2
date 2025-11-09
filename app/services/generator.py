from typing import List, Dict, Optional
from openai import OpenAI
import re
from dotenv import load_dotenv
import os
import tiktoken

load_dotenv()  # Charge automatiquement les variables d'environnement

# SYSTEM_PROMPT bienveillant et conversationnel
SYSTEM_PROMPT = """Tu es Coach Mike, un coach sportif motivant et à l'écoute.
Tu t'exprimes toujours en français, avec un ton positif, naturel et encourageant.
Tes réponses sont détaillées et progressives (exemples, variantes, conseils).
Tu utilises un style conversationnel, comme si tu parlais à un vrai sportif.
Tu adaptes ton ton au niveau et à l'objectif du sportif.
Tu peux t'appuyer sur les documents fournis, mais tu reformules toujours dans ton propre style.
Tu donnes des explications claires et structurées, tu encourages et tu reformules.
Si une source est pertinente, tu peux la citer naturellement.
Tu es chaleureux, professionnel et toujours positif."""

class RAGGenerator:
    """Generate answers given a query and retrieved documents."""

    def __init__(self, model: str = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")):
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Budget de contexte et plafond de docs (ENV) — valeurs plus généreuses pour réponses conversationnelles
        self.max_context_tokens = int(os.getenv("MAX_CONTEXT_TOKENS", "2000"))
        self.max_docs = int(os.getenv("MAX_DOCS", "5"))
        # Contrôle fin de la génération — plus de tokens pour réponses conversationnelles
        # Utilise OPENAI_MAX_TOKENS avec une valeur par défaut généreuse (1200 tokens)
        self.max_output_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1200"))
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))  # Plus créatif pour ton naturel
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

    def _build_prompt(self, query: str, context: List[Dict], profile: Optional[Dict] = None, is_first_message: bool = False) -> str:
        """
        Construit un prompt structuré et conversationnel.
        
        Args:
            query: Requête utilisateur (peut contenir le contexte conversationnel)
            context: Documents récupérés
            profile: Profil utilisateur (optionnel)
            is_first_message: True si c'est le premier message de la session
        """
        # Construire le contexte des documents - concaténer TOUS les documents
        # Utiliser directement doc.get("text") pour s'assurer qu'on utilise tous les documents
        context_parts = []
        for i, doc in enumerate(context):
            doc_text = doc.get("text", "") or doc.get("payload", {}).get("text", "")
            doc_title = doc.get("payload", {}).get("title", "") or doc.get("payload", {}).get("nom", "") or "Source"
            if doc_text:
                context_parts.append(f"[Document {i+1}] {doc_title}\n{doc_text}")
        
        context_text = "\n\n".join(context_parts)
        
        # Troncature du contexte pour éviter que le prompt soit trop long
        # Limite de sécurité : 4000 caractères pour laisser de la place pour la réponse
        max_context_chars = int(os.getenv("MAX_CONTEXT_CHARS", "4000"))
        if len(context_text) > max_context_chars:
            context_text = context_text[:max_context_chars] + "\n\n[... contexte tronqué ...]"
            print(f"[GENERATOR] Contexte tronqué à {max_context_chars} caractères")
        
        # Construire le contexte utilisateur
        user_context = ""
        if profile:
            user_context_parts = []
            if profile.get("niveau_sportif"):
                user_context_parts.append(f"Niveau: {profile['niveau_sportif']}")
            if profile.get("objectif_principal"):
                user_context_parts.append(f"Objectif: {profile['objectif_principal']}")
            if profile.get("materiel_disponible"):
                materiel = ", ".join(profile['materiel_disponible'])
                user_context_parts.append(f"Matériel disponible: {materiel}")
            if profile.get("zones_ciblees"):
                zones = ", ".join(profile['zones_ciblees'])
                user_context_parts.append(f"Zones ciblées: {zones}")
            
            if user_context_parts:
                user_context = "Profil utilisateur :\n" + "\n".join(f"- {part}" for part in user_context_parts) + "\n\n"
        
        # Salutation pour le premier message
        greeting = ""
        if is_first_message:
            greeting = "Bonjour ! Je suis Coach Mike, ravi de vous accompagner dans votre parcours sportif. "
        
        # Construire le prompt final - structuré et clair
        # Note: SYSTEM_PROMPT est déjà passé dans le message system, pas besoin de le répéter ici
        prompt = f"""{user_context}Documents pertinents :
{context_text}

Question : {query}

Coach Mike :"""
        
        print(f"[GENERATOR] Prompt construit avec {len(context)} documents, {len(context_text)} caractères de contexte")
        
        return prompt

    def generate(self, query: str, retrieved_docs: List[Dict], profile: Optional[Dict] = None, is_first_message: bool = False) -> Dict:
        """
        Génère une réponse conversationnelle basée sur les documents récupérés.
        
        Args:
            query: Requête utilisateur (peut contenir le contexte conversationnel)
            retrieved_docs: Documents récupérés par le retriever
            profile: Profil utilisateur (optionnel, pour personnalisation)
            is_first_message: True si c'est le premier message de la session
        
        Returns:
            Dict avec 'answer', 'sources', 'context_used'
        """
        # Pack le contexte avec un budget plus généreux pour réponses conversationnelles
        # S'assurer qu'on utilise tous les documents disponibles (au moins 3)
        context = self._pack_context(retrieved_docs, self.max_context_tokens)
        
        # S'assurer qu'on a au moins 3 documents pour un contexte riche
        # Si on a moins de 3 documents après packing, prendre les 3 meilleurs même si on dépasse le budget
        if len(context) < 3 and len(retrieved_docs) >= 3:
            # Prendre les 3 meilleurs documents même si on dépasse le budget
            context = sorted(retrieved_docs, key=lambda x: x.get('score', 0), reverse=True)[:3]
            print(f"[GENERATOR] Contexte enrichi : {len(context)} documents (minimum 3 requis)")
        elif len(context) < len(retrieved_docs):
            # Si on a plus de documents disponibles, essayer d'en utiliser plus
            # Prendre tous les documents si possible (dans la limite du budget)
            context = sorted(retrieved_docs, key=lambda x: x.get('score', 0), reverse=True)
            # Limiter par le budget de tokens
            token_count = 0
            final_context = []
            for doc in context:
                doc_tokens = len(self._enc.encode(doc.get('text', '')))
                if token_count + doc_tokens <= self.max_context_tokens:
                    final_context.append(doc)
                    token_count += doc_tokens
                else:
                    break
            if len(final_context) >= 3:
                context = final_context
                print(f"[GENERATOR] Contexte optimisé : {len(context)} documents utilisés (budget: {token_count}/{self.max_context_tokens} tokens)")
        
        print(f"[GENERATOR] Génération avec {len(context)} documents, temperature={self.temperature}, max_tokens={self.max_output_tokens}")
        
        # Construire le prompt structuré
        prompt = self._build_prompt(query, context, profile=profile, is_first_message=is_first_message)
        
        # Générer la réponse avec le SYSTEM_PROMPT bienveillant
        # Utiliser les paramètres du .env : LLM_TEMPERATURE, OPENAI_MAX_TOKENS, LLM_MODEL
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,  # LLM_TEMPERATURE (≈ 0.7)
            max_tokens=self.max_output_tokens  # OPENAI_MAX_TOKENS (≈ 1200)
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