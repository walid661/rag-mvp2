# main_api.py
import os
import uvicorn
import sys
from fastapi import FastAPI, Depends, HTTPException, Body, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# --- Validation Supabase ---
from supabase import create_client, Client

# --- Mode développement sans authentification ---
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "false").lower() == "true"

# --- Imports de MON RAG ---
sys.path.insert(0, os.path.abspath('.'))
from app.services.retriever import HybridRetriever
from app.services.generator import RAGGenerator
from app.services.rag_router import build_filters
from qdrant_client import QdrantClient

load_dotenv()

# --------------------------------------------------------------------------
# 1. CONFIGURATION ET INITIALISATION
# --------------------------------------------------------------------------

# --- Supabase Auth Config ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("ERREUR: SUPABASE_URL et SUPABASE_ANON_KEY doivent être définis dans .env")
    sys.exit(1)

# Initialise le client Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --- RAG Config ---
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "coach_mike")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")

# --- Initialisation des services RAG (au démarrage) ---
print("Initialisation du RAG Service...")
try:
    qdrant_client = QdrantClient(url=QDRANT_URL)
    retriever = HybridRetriever(
        qdrant_client=qdrant_client, 
        collection_name=COLLECTION_NAME,
        embedding_model=EMBEDDING_MODEL
    )
    generator = RAGGenerator()
    
    print("Chargement de l'index BM25...")
    if not retriever.load_bm25_state_if_any():
        print("Index BM25 non trouvé. Construction depuis Qdrant...")
        all_docs = qdrant_client.scroll(collection_name=COLLECTION_NAME, limit=10000, with_vectors=False)[0]
        retriever.build_bm25_index(all_docs)
        print("Index BM25 construit.")
    else:
        print("Index BM25 chargé.")
    print("RAG Service prêt.")
except Exception as e:
    print(f"ERREUR CRITIQUE RAG: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# --- FastAPI App ---
app = FastAPI(title="Coach IA RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les origines exactes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# 2. MODÈLES DE DONNÉES (Pydantic)
# --------------------------------------------------------------------------

class UserProfile(BaseModel):
    age: Optional[int] = None
    sexe: Optional[str] = None
    niveau_sportif: Optional[str] = None
    objectif_principal: Optional[str] = None
    frequence_hebdo: Optional[int] = None
    temps_disponible: Optional[int] = None
    materiel_disponible: Optional[List[str]] = Field(default_factory=list)
    zones_ciblees: Optional[List[str]] = Field(default_factory=list)
    contraintes_physiques: Optional[List[str]] = Field(default_factory=list)
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)
    experience_precedente: Optional[str] = None

class ChatRequest(BaseModel):
    query: str
    profile: UserProfile

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)

# --------------------------------------------------------------------------
# 3. DÉPENDANCE D'AUTHENTIFICATION (Supabase)
# --------------------------------------------------------------------------

async def get_current_user(authorization: str = Header(None)):
    """
    Vérifie le token JWT Supabase ou bypass si ENABLE_AUTH=false.
    Retourne toujours un dictionnaire standard pour compatibilité avec le reste du code.
    """
    if not ENABLE_AUTH:
        print("[AUTH] Mode développement : authentification désactivée")
        return {"id": "dev_user", "email": "dev@example.com"}

    if not authorization:
        print("[AUTH] ERREUR: Authorization header manquant")
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        print("[AUTH] ERREUR: Format Authorization invalide")
        raise HTTPException(status_code=401, detail="Invalid Authorization scheme")

    token = authorization.split(" ")[1]
    print(f"[AUTH] Token reçu (premiers 20 chars): {token[:20]}...")

    try:
        response = supabase.auth.get_user(token)
        user = response.user
        if not user:
            print("[AUTH] ERREUR: Token invalide (user null)")
            raise HTTPException(status_code=401, detail="Invalid token")
        print(f"[AUTH] Utilisateur authentifié: {user.id}")
        # Retourne un dictionnaire pour éviter les erreurs d'attributs
        return {"id": user.id, "email": user.email}
    except Exception as e:
        print(f"[AUTH] Erreur validation token: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=401, detail=f"Token invalide ou expiré: {str(e)}")

# --------------------------------------------------------------------------
# 4. LOGIQUE DE MAPPING (Le Cœur)
# --------------------------------------------------------------------------

def map_profile_to_rag_filters(profile: UserProfile, query: str = None) -> Dict[str, Any]:
    """
    Traduit le profil Supabase détaillé en un dict simple 
    que mon `rag_router.py: build_filters` peut comprendre.
    """
    rag_profile = {}

    if profile.niveau_sportif:
        rag_profile["niveau_sportif"] = profile.niveau_sportif
        
    if profile.objectif_principal:
        rag_profile["objectif_principal"] = profile.objectif_principal

    # --- Mapping de l'équipement ---
    if profile.materiel_disponible:
        materiel_lower = [m.lower() for m in profile.materiel_disponible]
        if any("barre" in m or "rack" in m or "machine" in m for m in materiel_lower):
            rag_profile["equipment"] = "full_gym"
        elif any("haltère" in m or "dumbbell" in m for m in materiel_lower):
            rag_profile["equipment"] = "dumbbell"
        elif any("élastique" in m or "band" in m for m in materiel_lower):
            rag_profile["equipment"] = "bands"
        elif any("aucun" in m or "poids du corps" in m or "bodyweight" in m for m in materiel_lower):
            rag_profile["equipment"] = "none"
        else:
            rag_profile["equipment"] = "none"
    else:
        rag_profile["equipment"] = "none"
    
    # CORRECTION : Passer zones_ciblees au rag_router
    if profile.zones_ciblees:
        rag_profile["zones_ciblees"] = profile.zones_ciblees

    print(f"Profil Supabase mappé en : {rag_profile}")
    return rag_profile

# --------------------------------------------------------------------------
# 5. ENDPOINT PRINCIPAL: /chat
# --------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat_with_coach(
    request: ChatRequest = Body(...),
    user: dict = Depends(get_current_user)
):
    """
    Endpoint principal pour interagir avec le coach IA.
    """
    import logging
    logging.basicConfig(level=logging.INFO)

    query = request.query
    profile = request.profile
    uid = user.get("id", "unknown")

    print(f"[CHAT] ========== Nouvelle requête ==========")
    print(f"[CHAT] UID: {uid}")
    print(f"[CHAT] Query: {query}")
    print(f"[CHAT] Profile: {profile.dict()}")

    if not query or not query.strip():
        print("[CHAT] ERREUR: Query vide")
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        # --- Logique RAG ---
        
        # 1. Mapper le profil Supabase en filtres RAG (avec query pour détection d'intention)
        rag_filters_profile = map_profile_to_rag_filters(profile, query=query)
        print(f"[CHAT] Profil mappé (query-aware): {rag_filters_profile}")
        
        # 2. Utiliser le rag_router.py
        # CORRECTION : Utiliser "auto" pour laisser la recherche sémantique décider
        # "auto" permet de chercher dans tous les types de documents (exercices, meso, micro)
        stage = "auto"
        
        # `build_filters` utilise le profil simple mappé + la query pour détecter l'intention
        filters = build_filters(stage=stage, profile=rag_filters_profile, extra={"query": query})
        print(f"[CHAT] Filtres RAG appliqués: {filters}")

        # 3. Utiliser le retriever
        retrieved_docs = retriever.retrieve(query, top_k=5, filters=filters)
        print(f"[CHAT] Documents trouvés: {len(retrieved_docs)}")
        
        # Log des scores pour diagnostic
        if retrieved_docs:
            scores = [f"{doc.get('score', 0.0):.3f}" for doc in retrieved_docs]
            top_score = retrieved_docs[0].get('score', 0.0) if retrieved_docs else 0.0
            print(f"[CHAT] Scores des documents: {scores}")
            print(f"[CHAT] Top score: {top_score:.3f}")

        if not retrieved_docs:
            answer = "Je n'ai pas trouvé de programme correspondant exactement à vos critères. Essayez de reformuler votre demande ou d'ajuster votre profil (par exemple, en changeant l'équipement ou l'objectif)."
            print("[CHAT] Aucun document trouvé, réponse par défaut")
            return ChatResponse(answer=answer, sources=[])

        # 4. Utiliser le generator
        # CORRECTION : Ne pas rejeter basé sur les scores RRF (qui sont naturellement faibles)
        # Laisser le LLM décider si le contexte est suffisant
        result = generator.generate(query, retrieved_docs)
        print("[CHAT] Réponse générée avec succès")
        
        return ChatResponse(answer=result["answer"], sources=result["sources"])
    except Exception as e:
        print(f"[CHAT] ERREUR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --------------------------------------------------------------------------
# 6. ENDPOINT DE SANTÉ
# --------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """Endpoint de santé pour vérifier que l'API fonctionne."""
    return {"status": "ok", "service": "Coach IA RAG API"}

# --------------------------------------------------------------------------
# 7. LANCEUR
# --------------------------------------------------------------------------

if __name__ == "__main__":
    print("Lancement du serveur API RAG sur http://localhost:8000")
    print("Assurez-vous que Qdrant est lancé.")
    print("Assurez-vous que SUPABASE_URL et SUPABASE_ANON_KEY sont dans .env")
    uvicorn.run(app, host="0.0.0.0", port=8000)

