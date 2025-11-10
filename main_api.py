# main_api.py
import os
import uvicorn
import sys
from fastapi import FastAPI, Depends, HTTPException, Body, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from collections import deque
from dotenv import load_dotenv

# --- Validation Supabase ---
from supabase import create_client, Client

# --- Charger les variables d'environnement AVANT de les utiliser ---
load_dotenv()

# --- Mode développement sans authentification ---
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "true").lower() == "true"
print(f"[CONFIG] ENABLE_AUTH = {ENABLE_AUTH} (valeur depuis .env: {os.getenv('ENABLE_AUTH', 'non définie')})")

# --- Imports de MON RAG ---
sys.path.insert(0, os.path.abspath('.'))
from app.services.retriever import HybridRetriever
from app.services.generator import RAGGenerator
from app.services.rag_router import build_filters
from qdrant_client import QdrantClient

# --------------------------------------------------------------------------
# 1. CONFIGURATION ET INITIALISATION
# --------------------------------------------------------------------------

# --- Supabase Auth Config ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Initialise le client Supabase seulement si l'auth est activée
if ENABLE_AUTH:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        print("ERREUR: SUPABASE_URL et SUPABASE_ANON_KEY doivent être définis dans .env quand ENABLE_AUTH=true")
        sys.exit(1)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
else:
    print("[CONFIG] Mode développement : authentification désactivée (ENABLE_AUTH=false)")
    supabase: Client = None  # type: ignore

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
# 4. MÉMOIRE DE SESSION
# --------------------------------------------------------------------------

# Mémoire courte par utilisateur (garde les 5 derniers échanges)
session_memory: Dict[str, deque] = {}

def get_context(uid: str) -> str:
    """Récupère le contexte conversationnel de l'utilisateur."""
    history = session_memory.get(uid, deque(maxlen=5))
    if not history:
        return ""
    return "\n".join(history)

def update_context(uid: str, user_message: str, coach_message: str) -> None:
    """Met à jour la mémoire de session avec un nouvel échange."""
    history = session_memory.setdefault(uid, deque(maxlen=5))
    history.append(f"Utilisateur: {user_message}")
    history.append(f"Coach: {coach_message}")

def clear_context(uid: str) -> None:
    """Efface la mémoire de session d'un utilisateur."""
    if uid in session_memory:
        session_memory[uid].clear()

# --------------------------------------------------------------------------
# 5. LOGIQUE DE MAPPING SÉMANTIQUE (Le Cœur)
# --------------------------------------------------------------------------

def map_profile_to_rag_filters(profile: UserProfile, query: str = "") -> Dict[str, Any]:
    """
    Traduit le profil Supabase détaillé en un dict enrichi pour le RAG.
    Analyse à la fois le profil et la requête pour un mapping sémantique intelligent.
    Supporte des valeurs multiples et des filtres souples.
    """
    rag_profile = {}
    query_lower = query.lower() if query else ""

    # --- Niveau sportif ---
    if profile.niveau_sportif:
        rag_profile["niveau_sportif"] = profile.niveau_sportif
    else:
        # Détection du niveau depuis la query si absent du profil
        if any(kw in query_lower for kw in ["débutant", "debutant", "beginner", "commence", "première"]):
            rag_profile["niveau_sportif"] = "Débutant"
        elif any(kw in query_lower for kw in ["intermédiaire", "intermediaire", "intermediate", "moyen"]):
            rag_profile["niveau_sportif"] = "Intermédiaire"
        elif any(kw in query_lower for kw in ["confirmé", "confirme", "avancé", "avance", "expert", "advanced"]):
            rag_profile["niveau_sportif"] = "Confirmé"
        else:
            rag_profile["niveau_sportif"] = "Débutant"  # Par défaut

    # --- Objectif principal ---
    if profile.objectif_principal:
        rag_profile["objectif_principal"] = profile.objectif_principal
    else:
        # Détection de l'objectif depuis la query
        if any(kw in query_lower for kw in ["perte de poids", "perte poids", "minceur", "maigrir", "sèche", "seche"]):
            rag_profile["objectif_principal"] = "Perte de poids"
        elif any(kw in query_lower for kw in ["prise de muscle", "muscle", "masse", "hypertrophie", "volume"]):
            rag_profile["objectif_principal"] = "Prise de muscle"
        elif any(kw in query_lower for kw in ["mobilité", "mobilite", "souplesse", "flexibilité", "flexibilite"]):
            rag_profile["objectif_principal"] = "Mobilité"
        elif any(kw in query_lower for kw in ["endurance", "cardio", "respiration", "souffle"]):
            rag_profile["objectif_principal"] = "Endurance"
        elif any(kw in query_lower for kw in ["force", "renforcement", "gainage", "tonification"]):
            rag_profile["objectif_principal"] = "Renforcement"

    # --- Zones ciblées (analyse sémantique depuis query + profil) ---
    zones = list(profile.zones_ciblees) if profile.zones_ciblees else []
    
    # Détection depuis la query
    if any(kw in query_lower for kw in ["biceps", "triceps", "bras", "épaule", "epaule", "épaules", "epaules"]):
        if "Membre supérieur" not in zones:
            zones.append("Membre supérieur")
    if any(kw in query_lower for kw in ["jambes", "cuisses", "quadriceps", "mollets", "fessiers", "fessier"]):
        if "Membre inférieur" not in zones:
            zones.append("Membre inférieur")
    if any(kw in query_lower for kw in ["dos", "lombaires", "dorsaux", "trapèzes", "trapezes"]):
        if "Chaîne postérieure" not in zones:
            zones.append("Chaîne postérieure")
    if any(kw in query_lower for kw in ["pec", "pectoraux", "poitrine", "torse", "abdos", "abdominaux", "core"]):
        if "Tronc" not in zones:
            zones.append("Tronc")
    
    # Si aucune zone détectée, utiliser "Full body" par défaut
    if not zones:
        zones = ["Full body"]
    
    rag_profile["zones_ciblees"] = zones

    # --- Mapping de l'équipement (avec support multi-valeurs) ---
    equipment_list = []
    if profile.materiel_disponible:
        materiel_lower = [m.lower() for m in profile.materiel_disponible]
        if any("barre" in m or "rack" in m or "machine" in m for m in materiel_lower):
            equipment_list.append("full_gym")
        if any("haltère" in m or "dumbbell" in m or "kettlebell" in m for m in materiel_lower):
            equipment_list.append("dumbbell")
        if any("élastique" in m or "band" in m for m in materiel_lower):
            equipment_list.append("bands")
        if any("tapis" in m or "mat" in m for m in materiel_lower):
            equipment_list.append("mat")
    
    # Détection depuis la query
    if any(kw in query_lower for kw in ["sans materiel", "sans matériel", "poids du corps", "bodyweight", "aucun"]):
        equipment_list.append("none")
    elif any(kw in query_lower for kw in ["haltère", "haltères", "dumbbell"]):
        if "dumbbell" not in equipment_list:
            equipment_list.append("dumbbell")
    
    # Par défaut, si rien n'est spécifié
    if not equipment_list:
        equipment_list = ["none"]
    
    rag_profile["equipment"] = equipment_list  # Liste pour support multi-valeurs

    print(f"[MAPPING] Profil mappé (query-aware): {rag_profile}")
    return rag_profile

# --------------------------------------------------------------------------
# 6. ENDPOINT PRINCIPAL: /chat
# --------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat_with_coach(
    request: ChatRequest = Body(...),
    user: dict = Depends(get_current_user)
):
    """
    Endpoint principal pour interagir avec le coach IA.
    Intègre la mémoire de session et un mapping sémantique intelligent.
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
        # --- Logique RAG avec mémoire de session ---
        
        # 1. Récupérer le contexte conversationnel
        context = get_context(uid)
        is_first_message = not context
        
        # 2. Construire la requête enrichie avec le contexte
        if context:
            full_query = f"{context}\n\nUtilisateur: {query}"
        else:
            full_query = query
        
        # 3. Mapper le profil Supabase en filtres RAG (avec analyse de la query)
        rag_filters_profile = map_profile_to_rag_filters(profile, query=query)
        print(f"[CHAT] Profil mappé (query-aware): {rag_filters_profile}")
        
        # 4. Utiliser le rag_router.py pour construire les filtres
        # Détection intelligente du stage selon la requête
        query_lower = query.lower()
        if any(kw in query_lower for kw in ["exercice", "exercices", "mouvement", "mouvements"]):
            stage = "pick_exercises"
        elif any(kw in query_lower for kw in ["micro", "microcycle", "micro-cycle"]):
            stage = "select_micro_patterns"
        elif any(kw in query_lower for kw in ["règle", "règles", "logique", "comment"]):
            stage = "micro_generation_rules"
        else:
            stage = "select_meso"  # Par défaut
        
        # `build_filters` utilise le profil enrichi avec valeurs multiples
        filters = build_filters(stage=stage, profile=rag_filters_profile)
        print(f"[CHAT] Filtres RAG appliqués: {filters}")

        # 5. Utiliser le retriever avec fallback
        retrieved_docs = retriever.retrieve(full_query, top_k=5, filters=filters)
        print(f"[CHAT] Documents trouvés: {len(retrieved_docs)}")
        
        # Log d'avertissement si contexte pauvre
        if len(retrieved_docs) < 3:
            print(f"[WARN] Contexte pauvre : moins de 3 documents ({len(retrieved_docs)}).")

        # Fallback : si aucun document trouvé, réessayer sans filtres stricts
        if not retrieved_docs:
            print("[CHAT] Aucun document avec filtres stricts, réessai avec filtres souples...")
            # Réessayer avec seulement domain et type
            soft_filters = {"domain": filters.get("domain"), "type": filters.get("type")}
            soft_filters = {k: v for k, v in soft_filters.items() if v}
            retrieved_docs = retriever.retrieve(full_query, top_k=3, filters=soft_filters if soft_filters else None)
            print(f"[CHAT] Documents trouvés (filtres souples): {len(retrieved_docs)}")

        # 6. Utiliser le generator avec le profil pour un contexte enrichi
        result = generator.generate(full_query, retrieved_docs, profile=profile.dict(), is_first_message=is_first_message)
        print("[CHAT] Réponse générée avec succès")
        
        # 7. Mettre à jour la mémoire de session
        update_context(uid, query, result["answer"])
        
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

