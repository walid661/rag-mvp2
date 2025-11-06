from typing import List, Dict
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class DocumentIndexer:
    """Create a Qdrant collection and index documents with embeddings."""

    def __init__(self, qdrant_url: str = "http://localhost:6333", collection_name: str = "coach_mike"):
        self.client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name

    def create_collection(self, vector_size: int = 768) -> None:
        """Recreate the collection with given vector size and cosine distance."""
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )

    def index_documents(self, documents: List[Dict], batch_size: int = 100) -> None:
        """Insert documents into the collection in batches."""
        points: List[PointStruct] = []
        for doc in documents:
            pid = uuid.uuid4().hex
            point = PointStruct(
                id=pid,
                vector=doc["embedding"],
                payload=doc["metadata"]
            )
            points.append(point)
            if len(points) >= batch_size:
                self.client.upsert(collection_name=self.collection_name, points=points)
                points = []
        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)