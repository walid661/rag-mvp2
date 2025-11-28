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
# --- CLIENTS ---
# Use Service Role Key if available to bypass RLS, otherwise fallback to Anon Key
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
KEY_TO_USE = SUPABASE_SERVICE_ROLE_KEY if SUPABASE_SERVICE_ROLE_KEY else SUPABASE_ANON_KEY

if not KEY_TO_USE:
    print("CRITICAL: No Supabase Key found (ANON or SERVICE_ROLE).")
    sys.exit(1)

if SUPABASE_SERVICE_ROLE_KEY:
    print("✅ USING SERVICE ROLE KEY (Bypassing RLS)")
else:
    print("⚠️ USING ANON KEY (Subject to RLS - might fail if not authenticated)")

supabase: Client = create_client(SUPABASE_URL, KEY_TO_USE)
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

class SaveProgramRequest(BaseModel):
    user_id: str
    title: str
    program_data: Dict[str, Any]

@app.post("/generate_plan")
async def generate_plan_endpoint(
    user: dict = Depends(verify_supabase_token),
    request_body: Optional[PlanRequest] = Body(None)
):
    """
    Generates a weekly training plan using RAG and LLM (Markdown output).
    """
    user_id = user["id"]
    print(f"📝 Generating plan for User: {user_id}")
    
    # 1. Fetch Profile from Supabase
    try:
        response = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="User profile not found. Please complete onboarding.")
        
        profile_data = response.data[0]
        
        level = profile_data.get("level", "Intermédiaire")
        goal = profile_data.get("goal", "Renforcement")
        equipment = profile_data.get("equipment", [])
        schedule = profile_data.get("days_per_week", 3)
        
    except Exception as e:
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # 2. Construct Prompt
    equipment_str = ", ".join(equipment) if equipment else "Bodyweight only"
    prompt = (
        f"Act as Coach Mike. Create a detailed 1-week training plan for a {level} user "
        f"who wants to {goal}. Equipment available: {equipment_str}. "
        f"Schedule: {schedule} days per week. "
        f"Use the retrieved documents to pick specific exercises and methods. "
        f"Output the plan in nicely formatted Markdown."
    )

    # 3. RAG Generation
    try:
        # Retrieve relevant docs (Mesocycles, Microcycles)
        # We use a broad query to get relevant training blocks
        retrieval_query = f"{goal} plan for {level} level using {equipment_str}"
        filters = build_filters(stage="auto", profile=profile_data, extra={"query": retrieval_query})
        
        retrieved_docs = retriever.retrieve(retrieval_query, top_k=5, filters=filters)
        
        # Generate Plan
        result = generator.generate(prompt, retrieved_docs)
        
        return {"plan_text": result["answer"]}
        
    except Exception as e:
        print(f"RAG Error: {e}")
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {str(e)}")

@app.post("/save_program")
async def save_program_endpoint(
    request: SaveProgramRequest,
    user: dict = Depends(verify_supabase_token)
):
    """
    Saves the generated program to Supabase.
    """
    if user["id"] != request.user_id:
        raise HTTPException(status_code=403, detail="User ID mismatch")

    try:
        data = {
            "user_id": request.user_id,
            "title": request.title,
            "program_data": request.program_data,
            "created_at": "now()"
        }
        response = supabase.table("saved_programs").insert(data).execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        print(f"Save Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save program: {str(e)}")

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

# --- SAVED PROGRAMS ENDPOINTS ---

class ProgramCreateRequest(BaseModel):
    title: str
    content: str  # Markdown text

@app.post("/api/programs")
async def create_program(
    request: ProgramCreateRequest,
    user: dict = Depends(verify_supabase_token)
):
    """
    Saves a new program.
    """
    try:
        data = {
            "user_id": user["id"],
            "title": request.title,
            "program_data": {"text": request.content},
            "created_at": "now()"
        }
        response = supabase.table("saved_programs").insert(data).execute()
        return {"status": "success", "data": response.data[0] if response.data else None}
    except Exception as e:
        print(f"Create Program Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create program: {str(e)}")

@app.get("/api/programs")
async def list_programs(
    user: dict = Depends(verify_supabase_token)
):
    """
    Returns a list of all programs for the authenticated user.
    """
    try:
        response = supabase.table("saved_programs")\
            .select("id, title, created_at")\
            .eq("user_id", user["id"])\
            .order("created_at", desc=True)\
            .execute()
        
        return {"data": response.data}
    except Exception as e:
        print(f"List Programs Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list programs: {str(e)}")

@app.get("/api/programs/{program_id}")
async def get_program(
    program_id: str,
    user: dict = Depends(verify_supabase_token)
):
    """
    Returns the full content of a specific program.
    """
    try:
        response = supabase.table("saved_programs")\
            .select("*")\
            .eq("id", program_id)\
            .eq("user_id", user["id"])\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Program not found")
            
        program = response.data[0]
        # Extract markdown content for convenience, but return full object
        content = program.get("program_data", {}).get("text", "")
        
        return {"data": program, "content": content}
    except Exception as e:
        print(f"Get Program Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get program: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
