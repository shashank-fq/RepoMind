"""enable pgvector"""
revision = '000_enable_pgvector'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

def downgrade():
    op.execute("DROP EXTENSION IF EXISTS vector")