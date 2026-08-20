
from app.services.embeddings.local import LocalSentenceTransformerProvider

def test_local_embedding_provider():
    provider = LocalSentenceTransformerProvider(model_name="all-MiniLM-L6-v2")
    assert provider.dimension == 384

    texts = ["def login_user(username, password): pass", "class DatabaseConnector: pass"]
    vectors = provider.embed_texts(texts)

    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384
    assert isinstance(vectors[0][0], float)