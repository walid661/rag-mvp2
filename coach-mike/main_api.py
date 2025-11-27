import os
import sys
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from supabase import create_client, Client

# --- SETUP PATHS ---
# Add root directory to sys.path to import scripts and app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.retriever import HybridRetriever
from app.services.generator import RAGGenerator
from app.services.rag_router import build_filters
from scripts.generate_plan import generate_weekly_plan
from qdrant_client import QdrantClient

load_dotenv()

# --- CONFIGURATION ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "coach_mike")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "true").lower() == "true"

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("CRITICAL: Supabase credentials missing.")
    sys.exit(1)

# --- CLIENTS ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
qdrant_client = QdrantClient(url=QDRANT_URL)

# Initialize RAG Services
try:
    retriever = HybridRetriever(
        qdrant_client=qdrant_client, 
        collection_name=COLLECTION_NAME,
        embedding_model=EMBEDDING_MODEL
    )
    generator = RAGGenerator()
    print("✅ RAG Services Initialized")
except Exception as e:
    print(f"❌ RAG Init Failed: {e}")
    sys.exit(1)

app = FastAPI(title="Coach Mike AI Microservice", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELS ---
class ChatRequest(BaseModel):
    query: str
    context_exercise: Optional[Dict[str, Any]] = None

class PlanRequest(BaseModel):
    # We might accept overrides here, but primarily we use the DB profile
    pass

# --- AUTH MIDDLEWARE ---
async def verify_supabase_token(authorization: str = Header(None)) -> Dict[str, Any]:
    """
    Verifies the JWT token with Supabase.
    Returns the user object if valid.
    """
    if not ENABLE_AUTH:
        # Dev bypass
        return {"id": "dev_user_123", "email": "dev@example.com"}

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization scheme")

    token = authorization.split(" ")[1]
    
    try:
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"id": user.user.id, "email": user.user.email}
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(status_code=401, detail="Token verification failed")

# --- ENDPOINTS ---

@app.get("/health")
def health_check():
    return {"status": "active", "service": "Coach Mike AI"}

@app.post("/generate_plan")
async def generate_plan_endpoint(
    user: dict = Depends(verify_supabase_token)
):
    """
    Generates a weekly training plan based on the user's profile in Supabase.
    """
    user_id = user["id"]
    print(f"📝 Generating plan for User: {user_id}")
    
    # 1. Fetch Profile from Supabase
    try:
        response = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="User profile not found. Please complete onboarding.")
        
        profile_data = response.data[0]
        
        # Map DB fields to Script expected format
        # DB: level, goal, equipment (json), days_per_week
        # Script expects: level, goal, schedule, equipment (list)
        script_profile = {
            "level": profile_data.get("level", "Intermédiaire"),
            "goal": profile_data.get("goal", "Renforcement"),
            "schedule": profile_data.get("days_per_week", 3),
            "equipment": profile_data.get("equipment", [])
        }
        
    except Exception as e:
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # 2. Call Planner Agent Logic
    try:
        plan = generate_weekly_plan(script_profile)
        if "error" in plan:
            raise HTTPException(status_code=400, detail=plan["error"])
        
        return plan
    except Exception as e:
        print(f"Planner Error: {e}")
        raise HTTPException(status_code=500, detail=f"Planning failed: {str(e)}")

@app.post("/chat_coach")
async def chat_coach_endpoint(
    request: ChatRequest = Body(...),
    user: dict = Depends(verify_supabase_token)
):
    """
    RAG Chat endpoint.
    """
    query = request.query
    print(f"💬 Chat Query from {user['id']}: {query}")
    
    try:
        # 1. Retrieve Documents
        # We could use user profile to filter, but for now let's keep it broad or use 'auto'
        filters = build_filters(stage="auto", profile={}, extra={"query": query})
        
        retrieved_docs = retriever.retrieve(query, top_k=5, filters=filters)
        
        if not retrieved_docs:
            return {"answer": "I couldn't find specific information in my database to answer that. Could you rephrase?", "sources": []}

        # 2. Generate Answer
        result = generator.generate(query, retrieved_docs)
        
        return {
            "answer": result["answer"],
            "sources": result["sources"]
        }
        
    except Exception as e:
        print(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
