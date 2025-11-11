# app/services/ingest_logic_jsonl.py
import json
from pathlib import Path
from typing import Dict, Any, Iterable, List
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

# Import de l'indexer existant
from app.services.indexer import DocumentIndexer

# ============================================================================
# VERSION ORIGINALE : Données dans data/raw/ (commentées pour utiliser v2)
# ============================================================================
# DATA_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
# LOGIC_DIR = DATA_ROOT / "logic_jsonl"
# EXO_NEW_DIR = DATA_ROOT / "exercices_new"

# ============================================================================
# CONFIGURATION : Définition explicite des sources de données
# ============================================================================
DATA_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
DATA_ROOT_V2 = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "raw_v2"

# Liste explicite des fichiers JSONL à ingérer (dans l'ordre de priorité)
LOGIC_JSONL_FILES = [
    "meso_catalog.jsonl",           # Programmes meso-cycles
    "micro_catalog.jsonl",          # Programmes micro-cycles
    "macro_to_micro_rules.jsonl",   # Règles macro → micro
    "generation_spec.jsonl",         # Spécifications de génération
    "objective_priority.jsonl",      # Priorités d'objectifs
    "planner_schema.jsonl",          # Schéma du planificateur
    "muscle_balance_rules.jsonl",    # Règles d'équilibrage musculaire (v2 uniquement)
    "balanced_session_examples.jsonl", # Exemples de séances équilibrées (v2 uniquement)
]

# Fichiers à ignorer (schémas et exemples non indexables)
SKIP_FILES = {"planner_examples.jsonl", "user_profile_schema.jsonl"}

# Détermination automatique de la version à utiliser (v2 prioritaire, fallback original)
USE_V2 = False
LOGIC_DIR = None
EXO_NEW_DIR = None

if (DATA_ROOT_V2 / "logic_jsonl_v2").exists() and (DATA_ROOT_V2 / "exercices_new_v2").exists():
    # VERSION V2 : Données enrichies
    USE_V2 = True
    LOGIC_DIR = DATA_ROOT_V2 / "logic_jsonl_v2"
    EXO_NEW_DIR = DATA_ROOT_V2 / "exercices_new_v2"
    print(f"[ingest] ===== MODE V2 ACTIVÉ =====")
    print(f"[ingest] Source règles: {LOGIC_DIR}")
    print(f"[ingest] Source exercices: {EXO_NEW_DIR}")
else:
    # VERSION ORIGINALE : Fallback
    USE_V2 = False
    LOGIC_DIR = DATA_ROOT / "logic_jsonl"
    EXO_NEW_DIR = DATA_ROOT / "exercices_new"
    print(f"[ingest] ===== MODE ORIGINAL (fallback) =====")
    print(f"[ingest] WARN: Données v2 non trouvées, utilisation données originales")
    print(f"[ingest] Source règles: {LOGIC_DIR}")
    print(f"[ingest] Source exercices: {EXO_NEW_DIR}")

def _read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    """Lit un fichier JSONL ligne par ligne."""
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue

def _build_doc_from_record(file_name: str, rec: Dict[str, Any]) -> Dict[str, Any]:
    """Construit un document indexable depuis un record JSONL selon le mapping canonique."""
    source = rec.get("source") or file_name

    # Mapping filename -> domain/type/embedding_text
    if file_name == "meso_catalog.jsonl":
        domain, typ, text = "program", "meso_ref", rec.get("text", "")
    elif file_name == "micro_catalog.jsonl":
        domain, typ, text = "program", "micro_ref", rec.get("text", "")
    elif file_name == "macro_to_micro_rules.jsonl":
        domain, typ, text = "logic", rec.get("type", "rule"), rec.get("rule_text", "")
    elif file_name == "generation_spec.jsonl":
        domain, typ, text = "logic", rec.get("type", "rule"), rec.get("rule_text", "")
    elif file_name == "planner_schema.jsonl":
        domain, typ, text = "logic", rec.get("type", "planner_rule"), rec.get("rule_text", "")
        # Aide au filtrage : si fields.blocks existe, duplique à plat
        fields = rec.get("fields") or {}
        if "blocks" in fields:
            rec["blocks"] = fields["blocks"]
    elif file_name == "objective_priority.jsonl":
        domain, typ, text = "logic", "objective_priority", rec.get("rule_text", "")
    else:
        # Par défaut (au cas où)
        domain, typ, text = "logic", rec.get("type", "rule"), rec.get("rule_text") or rec.get("text", "")

    # Copie du record pour le payload
    doc = dict(rec)
    
    # Champs canoniques obligatoires
    doc["domain"] = domain
    doc["type"] = typ
    doc["source"] = source
    
    # IMPORTANT : Générer un texte de fallback si text est vide
    if not text or text.strip() == "":
        # Construire un texte à partir des métadonnées disponibles
        text_parts = []
        if rec.get("nom"):
            text_parts.append(rec["nom"])
        if rec.get("name"):
            text_parts.append(rec["name"])
        if rec.get("title"):
            text_parts.append(rec["title"])
        if rec.get("groupe"):
            text_parts.append(f"Groupe: {rec['groupe']}")
        if rec.get("objectif"):
            text_parts.append(f"Objectif: {rec['objectif']}")
        if rec.get("niveau"):
            text_parts.append(f"Niveau: {rec['niveau']}")
        if rec.get("methode"):
            text_parts.append(f"Méthode: {rec['methode']}")
        if rec.get("rule_text"):
            text_parts.append(rec["rule_text"])
        
        text = ". ".join(text_parts) if text_parts else f"Document {domain}/{typ}"
    
    doc["text"] = text  # IMPORTANT : texte passé à l'embedder

    # S'assurer que 'domain' est présent dans le payload final (via meta)
    # L'indexer fusionne **meta, donc domain doit être dans meta pour arriver dans le payload
    doc["meta"] = {**doc.get("meta", {}), "domain": domain, "type": typ}
    
    # Ajouter les champs de filtrage importants au meta pour qu'ils soient dans le payload
    # Ces champs sont utilisés par le retriever pour filtrer les documents
    if rec.get("niveau"):
        doc["meta"]["niveau"] = rec["niveau"]
    if rec.get("groupe"):
        doc["meta"]["groupe"] = rec["groupe"]
    if rec.get("objectif"):
        doc["meta"]["objectif"] = rec["objectif"]
    if rec.get("methode"):
        doc["meta"]["methode"] = rec["methode"]
    if rec.get("equipment"):
        doc["meta"]["equipment"] = rec["equipment"]
    
    # (facultatif mais utile) aplatir un driver pour filtrer plus simplement
    # Si conditions.driver existe, le dupliquer en conditions_driver pour filtrage direct
    if isinstance(rec.get("conditions"), dict) and "driver" in rec["conditions"]:
        doc["meta"]["conditions_driver"] = rec["conditions"]["driver"]

    # Nettoyage : pas de champ "embedding" dans le payload
    if "embedding" in doc:
        del doc["embedding"]

    return doc

def _embed_texts(model: SentenceTransformer, texts: List[str]) -> List[List[float]]:
    """Encode les textes avec le même modèle que le retriever."""
    return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True).tolist()

def ingest_logic_and_program_jsonl(
    qdrant_url: str = None,
    collection_name: str = None,
    embedding_model: str = None
) -> int:
    """
    Ingère tous les JSONL de logic_jsonl/ (sauf ceux dans SKIP_FILES) et les exercices.
    
    Args:
        qdrant_url: URL Qdrant (défaut: env)
        collection_name: Nom de la collection (défaut: env)
        embedding_model: Modèle d'embedding (défaut: env ou all-mpnet-base-v2)
    
    Returns:
        Nombre de documents indexés
    """
    # Initialisation avec les mêmes paramètres que le retriever
    if embedding_model is None:
        embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
    
    print(f"[ingest] Chargement du modèle d'embedding: {embedding_model}")
    model = SentenceTransformer(embedding_model)
    
    indexer = DocumentIndexer(
        qdrant_url=qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6335"),
        collection_name=collection_name or os.getenv("QDRANT_COLLECTION", "coach_mike")
    )
    
    docs: List[Dict[str, Any]] = []

    # 1. Ingestion des JSONL de logic_jsonl/ (fichiers explicites uniquement)
    if LOGIC_DIR.exists():
        print(f"[ingest] === Ingestion des règles et programmes ===")
        print(f"[ingest] Fichiers attendus: {', '.join(LOGIC_JSONL_FILES)}")
        
        files_found = 0
        files_skipped = 0
        files_missing = []
        
        for file_name in LOGIC_JSONL_FILES:
            path = LOGIC_DIR / file_name
            
            if file_name in SKIP_FILES:
                print(f"[ingest] ⏭️  Ignoré (SKIP): {file_name}")
                files_skipped += 1
                continue
            
            if not path.exists():
                if USE_V2 and file_name in ["muscle_balance_rules.jsonl", "balanced_session_examples.jsonl"]:
                    # Ces fichiers sont optionnels en v2
                    print(f"[ingest] ⚠️  Optionnel (v2): {file_name} non trouvé")
                else:
                    print(f"[ingest] ⚠️  Manquant: {file_name}")
                    files_missing.append(file_name)
                continue
            
            print(f"[ingest] 📄 Lecture de {file_name}...")
            count = 0
            for rec in _read_jsonl(path):
                doc = _build_doc_from_record(file_name, rec)
                docs.append(doc)
                count += 1
            print(f"[ingest]   ✅ {count} documents chargés depuis {file_name}")
            files_found += 1
        
        print(f"[ingest] Résumé règles: {files_found} fichiers lus, {files_skipped} ignorés, {len(files_missing)} manquants")
        if files_missing:
            print(f"[ingest] ⚠️  Fichiers manquants: {', '.join(files_missing)}")
    else:
        print(f"[ingest] ❌ ERREUR: Dossier {LOGIC_DIR} non trouvé")

    # 2. Ingestion des exercices depuis exercices_new/ (tous les .json)
    if EXO_NEW_DIR.exists():
        exo_files = list(EXO_NEW_DIR.glob("*.json"))
        if exo_files:
            print(f"[ingest] === Ingestion des exercices ===")
            print(f"[ingest] Source: {EXO_NEW_DIR}")
            print(f"[ingest] Fichiers trouvés: {len(exo_files)} exercices .json")
            exo_count = 0
            for exo_path in sorted(exo_files):
                try:
                    exo = json.loads(exo_path.read_text(encoding="utf-8"))
                except Exception as e:
                    print(f"[ingest] ERREUR lecture {exo_path.name}: {e}")
                    continue
                
                # Mapping exercice nouveau format
                exo["domain"] = "exercise"
                exo["type"] = "exercise"
                exo["source"] = exo.get("source") or "exercices_new"
                
                # Texte pour embedding : utiliser le champ text (déjà généré par OpenAI)
                text = exo.get("text", "")
                if not text or text.strip() == "":
                    # Fallback : construire depuis les champs disponibles
                    text_parts = []
                    if exo.get("exercise"):
                        text_parts.append(exo["exercise"])
                    if exo.get("target_muscle_group"):
                        text_parts.append(f"Muscles ciblés: {exo['target_muscle_group']}")
                    if exo.get("primary_equipment"):
                        text_parts.append(f"Équipement: {exo['primary_equipment']}")
                    text = ". ".join(text_parts) if text_parts else f"Exercice {exo.get('exercise', 'inconnu')}"
                    exo["text"] = text
                
                # IMPORTANT : Extraire tous les champs français pour le payload (filtrage)
                # Ces champs seront utilisés par rag_router.py pour construire les filtres
                exo["meta"] = {**exo.get("meta", {}), "domain": "exercise", "type": "exercise"}
                
                # Mapper les champs français au niveau racine ET dans meta pour filtrage
                # Champs principaux pour filtrage :
                if exo.get("difficulty_level"):
                    exo["difficulty_level"] = exo["difficulty_level"]  # Français
                    exo["meta"]["difficulty_level"] = exo["difficulty_level"]
                    # Compatibilité : aussi mapper vers "niveau" pour compatibilité avec ancien code
                    exo["niveau"] = exo["difficulty_level"]
                    exo["meta"]["niveau"] = exo["difficulty_level"]
                
                # NOUVEAUX CHAMPS ENRICHIS (v2) : Si disponibles, les ajouter au payload
                # Ces champs permettront l'équilibrage musculaire et la variété des exercices
                if exo.get("antagonist_muscle_group"):
                    exo["antagonist_muscle_group"] = exo["antagonist_muscle_group"]
                    exo["meta"]["antagonist_muscle_group"] = exo["antagonist_muscle_group"]
                
                if exo.get("secondary_muscle_groups"):
                    exo["secondary_muscle_groups"] = exo["secondary_muscle_groups"]
                    exo["meta"]["secondary_muscle_groups"] = exo["secondary_muscle_groups"]
                
                if exo.get("exercise_family"):
                    exo["exercise_family"] = exo["exercise_family"]
                    exo["meta"]["exercise_family"] = exo["exercise_family"]
                
                if exo.get("target_muscle_group"):
                    exo["target_muscle_group"] = exo["target_muscle_group"]  # Français
                    exo["meta"]["target_muscle_group"] = exo["target_muscle_group"]
                    # Compatibilité : aussi mapper vers "zone" pour compatibilité
                    exo["zone"] = exo["target_muscle_group"]
                    exo["meta"]["zone"] = exo["target_muscle_group"]
                
                if exo.get("primary_equipment"):
                    exo["primary_equipment"] = exo["primary_equipment"]  # Français
                    exo["meta"]["primary_equipment"] = exo["primary_equipment"]
                    # Compatibilité : aussi mapper vers "equipment" et "materiel"
                    exo["equipment"] = exo["primary_equipment"]
                    exo["materiel"] = exo["primary_equipment"]
                    exo["meta"]["equipment"] = exo["primary_equipment"]
                    exo["meta"]["materiel"] = exo["primary_equipment"]
                
                if exo.get("body_region"):
                    exo["body_region"] = exo["body_region"]
                    exo["meta"]["body_region"] = exo["body_region"]
                
                if exo.get("movement_pattern"):
                    exo["movement_pattern"] = exo["movement_pattern"]
                    exo["meta"]["movement_pattern"] = exo["movement_pattern"]
                
                if exo.get("mechanics"):
                    exo["mechanics"] = exo["mechanics"]
                    exo["meta"]["mechanics"] = exo["mechanics"]
                
                # Tous les autres champs français aussi dans meta pour filtrage avancé
                for key, value in exo.items():
                    if key.endswith("_en"):
                        continue  # Ignorer les champs anglais
                    if key not in ["text", "domain", "type", "source", "meta", "embedding"]:
                        exo["meta"][key] = value
                
                docs.append(exo)
                exo_count += 1
                if exo_count % 100 == 0:
                    print(f"[ingest]   ⏳ {exo_count}/{len(exo_files)} exercices chargés...")
            print(f"[ingest]   ✅ Total: {exo_count} exercices chargés depuis {EXO_NEW_DIR}")
        else:
            print(f"[ingest] ⚠️  Aucun fichier .json trouvé dans {EXO_NEW_DIR}")
    else:
        print(f"[ingest] ❌ ERREUR: Dossier {EXO_NEW_DIR} non trouvé")

    # Résumé final
    print(f"[ingest] ===== RÉSUMÉ INGESTION =====")
    print(f"[ingest] Mode: {'V2 (enrichi)' if USE_V2 else 'ORIGINAL (fallback)'}")
    print(f"[ingest] Total documents préparés: {len(docs)}")
    print(f"[ingest]   - Règles/Programmes: {len([d for d in docs if d.get('domain') != 'exercise'])}")
    print(f"[ingest]   - Exercices: {len([d for d in docs if d.get('domain') == 'exercise'])}")
    
    if not docs:
        print("[ingest] ❌ ERREUR: Aucun document à indexer.")
        return 0

    # 3. Génération des embeddings
    print(f"[ingest] Génération des embeddings pour {len(docs)} documents...")
    texts = [d.get("text", "") for d in docs]
    vecs = _embed_texts(model, texts)
    for d, v in zip(docs, vecs):
        d["embedding"] = v

    # 4. Indexation
    print(f"[ingest] Indexation de {len(docs)} documents dans Qdrant...")
    indexer.index_documents(docs)
    print(f"[ingest] ✅ {len(docs)} documents indexés avec succès")
    
    return len(docs)

if __name__ == "__main__":
    import argparse
    from sentence_transformers import SentenceTransformer
    from app.services.indexer import DocumentIndexer

    parser = argparse.ArgumentParser(description="Ingest logic/program JSONL into Qdrant")
    parser.add_argument("--reset", action="store_true", help="Drop & recreate the Qdrant collection before ingest")
    parser.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL"), help="Qdrant URL (env QDRANT_URL)")
    parser.add_argument("--collection", default=os.getenv("QDRANT_COLLECTION", "coach_mike"), help="Collection name")
    parser.add_argument("--embedding-model", default=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2"), help="Embedding model name")
    args = parser.parse_args()

    # 1) Déterminer la dimension du modèle d'embedding (cohérent avec le retriever)
    print(f"[ingest] Chargement du modèle pour dimension: {args.embedding_model}")
    model = SentenceTransformer(args.embedding_model)
    vector_size = model.get_sentence_embedding_dimension()
    print(f"[ingest] Dimension du vecteur: {vector_size}")

    # 2) Instancier l'indexer avec la même collection
    qdrant_url = args.qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6335")
    collection_name = args.collection or os.getenv("QDRANT_COLLECTION", "coach_mike")
    
    indexer = DocumentIndexer(
        qdrant_url=qdrant_url,
        collection_name=collection_name
    )

    # 3) Reset optionnel
    if args.reset:
        print(f"[ingest] RESET demandé → drop + recreate '{collection_name}' ({vector_size} dims)")
        # Cette méthode existe déjà dans DocumentIndexer
        indexer.create_collection(vector_size=vector_size)

    # 4) Ingestion standard (réutilise la logique existante)
    ingest_logic_and_program_jsonl(
        qdrant_url=qdrant_url,
        collection_name=collection_name,
        embedding_model=args.embedding_model,
    )

