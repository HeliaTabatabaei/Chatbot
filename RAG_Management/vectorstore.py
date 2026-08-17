# vectorstore.py
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    SparseVectorParams,
    SparseIndexParams,
    Modifier
)
from config import QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME, VECTOR_SIZE


def get_client():
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ensure_collection(client: QdrantClient):
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            # Dense vector (OpenAI embedding)
            vectors_config={
                "dense": VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            },
            # Sparse vector (BM25)
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    index=SparseIndexParams(
                        on_disk=False  # maintain in RAM for speed
                    ),
                    modifier=Modifier.IDF  # TF-IDF weighting
                )
            }
        )
        print(f"Collection '{COLLECTION_NAME}' created with hybrid search support.")
    else:
        print(f"Collection '{COLLECTION_NAME}' already exists.")
