import gradio as gr
import requests
import json

# Configuration simple
API_URL = "http://localhost:8000/chat"

def chat_stream(message, history, niveau, objectif, materiel):
    """
    Version simplifiée pour tester rapidement la connexion au backend RAG.
    """
    # Construire le profil utilisateur
    profile = {
        "age": 30,
        "sexe": "homme",
        "niveau_sportif": niveau,
        "objectif_principal": objectif,
        "frequence_hebdo": 3,
        "temps_disponible": 45,
        "materiel_disponible": [m.strip() for m in materiel.split(",") if m.strip()],
        "zones_ciblees": [],
        "contraintes_physiques": [],
        "preferences": {},
        "experience_precedente": ""
    }
    
    # Préparer la requête
    payload = {
        "query": message,
        "profile": profile
    }
    
    try:
        # Appeler l'API (sans auth en mode dev)
        response = requests.post(
            API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "Pas de réponse")
            
            # Ajouter les sources si présentes
            sources = data.get("sources", [])
            if sources:
                answer += "\n\n📚 Sources:"
                for src in sources[:3]:  # Limiter à 3 sources
                    answer += f"\n• Doc {src.get('index', '?')}"
                    if src.get('type'):
                        answer += f" ({src['type']})"
            
            return answer
        else:
            return f"❌ Erreur: {response.status_code} - {response.text[:200]}"
            
    except requests.exceptions.ConnectionError:
        return "❌ API non disponible. Lancez d'abord: python main_api.py"
    except Exception as e:
        return f"❌ Erreur: {str(e)}"

# Interface Gradio simple
demo = gr.ChatInterface(
    fn=chat_stream,
    title="🏋️ Coach IA - Fitness RAG",
    description="Posez vos questions sur l'entraînement et le fitness",
    examples=[
        "Propose-moi un programme pour débutant",
        "Exercices pour les jambes sans matériel",
        "Comment améliorer ma force ?",
    ],
    additional_inputs=[
        gr.Dropdown(
            choices=["Débutant", "Intermédiaire", "Confirmé"],
            value="Intermédiaire",
            label="Niveau"
        ),
        gr.Dropdown(
            choices=[
                "Perte de poids",
                "Renforcement",
                "Force",
                "Cardio",
                "Mobilité"
            ],
            value="Renforcement",
            label="Objectif"
        ),
        gr.Textbox(
            value="haltères, tapis",
            label="Matériel (séparé par des virgules)",
            placeholder="Ex: haltères, élastiques, barre"
        )
    ],
    retry_btn=None,
    undo_btn="Annuler",
    clear_btn="Effacer"
)

if __name__ == "__main__":
    print("🚀 Lancement du chatbot...")
    print("⚠️  Assurez-vous que l'API est lancée: python main_api.py")
    demo.launch(server_port=7860)
