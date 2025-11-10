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

DATA_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
LOGIC_DIR = DATA_ROOT / "logic_jsonl"
EXO_DIR = DATA_ROOT / "exercises_json"

SKIP_FILES = {"planner_examples.jsonl", "user_profile_schema.jsonl"}

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

    # 1. Ingestion des JSONL de logic_jsonl/
    if LOGIC_DIR.exists():
        for path in sorted(LOGIC_DIR.glob("*.jsonl")):
            if path.name in SKIP_FILES:
                print(f"[ingest] Ignoré: {path.name}")
                continue
            
            print(f"[ingest] Lecture de {path.name}...")
            count = 0
            for rec in _read_jsonl(path):
                doc = _build_doc_from_record(path.name, rec)
                docs.append(doc)
                count += 1
            print(f"[ingest]   {count} documents chargés depuis {path.name}")
    else:
        print(f"[ingest] WARN: Dossier {LOGIC_DIR} non trouvé")

    # 2. Optionnel : exercices (si on veut aussi les recharger ici)
    if EXO_DIR.exists():
        print(f"[ingest] Lecture des exercices depuis {EXO_DIR}...")
        exo_count = 0
        for exo_path in sorted(EXO_DIR.glob("*.json")):
            try:
                exo = json.loads(exo_path.read_text(encoding="utf-8"))
            except Exception as e:
                continue
            
            # Mapping exercice
            exo["domain"] = "exercise"
            exo["type"] = "exercise"
            exo["source"] = exo.get("source") or "exercises_json"
            # Texte pour embedding : text (champ principal) ou title comme fallback
            text = exo.get("text") or exo.get("title", "")
            
            # IMPORTANT : Générer un texte de fallback si text est vide
            if not text or text.strip() == "":
                # Construire un texte à partir des métadonnées disponibles
                text_parts = []
                if exo.get("title"):
                    text_parts.append(exo["title"])
                if exo.get("id"):
                    text_parts.append(f"ID: {exo['id']}")
                if exo.get("category"):
                    text_parts.append(f"Catégorie: {exo['category']}")
                if exo.get("type"):
                    text_parts.append(f"Type: {exo['type']}")
                if exo.get("level"):
                    text_parts.append(f"Niveau: {exo['level']}")
                
                text = ". ".join(text_parts) if text_parts else f"Exercice {exo.get('id', 'inconnu')}"
            
            exo["text"] = text
            
            # S'assurer que equipment est présent si disponible (clé de filtre)
            if "equipment" not in exo and exo.get("materiel"):
                exo["equipment"] = exo["materiel"]
            
            # Mettre domain dans meta pour le payload
            exo["meta"] = {**exo.get("meta", {}), "domain": "exercise", "type": "exercise"}
            
            docs.append(exo)
            exo_count += 1
            if exo_count % 100 == 0:
                print(f"[ingest]   {exo_count} exercices chargés...")
        print(f"[ingest]   Total: {exo_count} exercices chargés")
    else:
        print(f"[ingest] WARN: Dossier {EXO_DIR} non trouvé")

    if not docs:
        print("[ingest] Aucun document à indexer.")
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

