import sys
import os

# Add the project root to the path so imports work
sys.path.append(os.getcwd())

print("Checking imports...")
try:
    from app.services import rag_router
    print("[OK] app.services.rag_router imported successfully")
except Exception as e:
    print(f"[FAIL] Failed to import app.services.rag_router: {e}")
    sys.exit(1)

try:
    # We need to mock environment variables that main_api expects
    os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
    os.environ["SUPABASE_ANON_KEY"] = "mock_key"
    
    # main_api imports from app.services, so we need to be careful
    from coach_mike import main_api
    print("[OK] coach-mike/main_api imported successfully")
except Exception as e:
    print(f"[FAIL] Failed to import coach-mike/main_api: {e}")
    sys.exit(1)

print("All checks passed.")
