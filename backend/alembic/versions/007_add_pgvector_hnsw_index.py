"""Add HNSW index to code_chunks embedding column

Revision ID: 007_add_hnsw_index
Revises: 006_embedding_column
Create Date: 2026-08-22
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '007_add_hnsw_index'
down_revision = '006_embedding_column'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create HNSW index using pgvector cosine operators (vector_cosine_ops)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS code_chunks_embedding_hnsw_idx 
        ON code_chunks 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
        """
    )

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS code_chunks_embedding_hnsw_idx;")