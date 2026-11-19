"""Chat history and PO drafts in the assistant schema.

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE assistant.conversations (
        id text PRIMARY KEY,
        user_id text NOT NULL,
        title text NOT NULL,
        created_at timestamptz NOT NULL,
        updated_at timestamptz NOT NULL,
        is_deleted boolean NOT NULL DEFAULT false
    );
    CREATE INDEX ix_conversations_user_updated
        ON assistant.conversations (user_id, updated_at DESC);

    CREATE TABLE assistant.messages (
        id text PRIMARY KEY,
        seq bigint GENERATED ALWAYS AS IDENTITY,
        conversation_id text NOT NULL
            REFERENCES assistant.conversations (id) ON DELETE CASCADE,
        sender text NOT NULL CHECK (sender IN ('user', 'assistant')),
        text text NOT NULL,
        payload jsonb NOT NULL DEFAULT '{}'::jsonb,
        langsmith_run_id text,
        feedback smallint CHECK (feedback IN (-1, 1)),
        created_at timestamptz NOT NULL
    );
    CREATE INDEX ix_messages_conversation_created
        ON assistant.messages (conversation_id, seq);

    CREATE TABLE assistant.po_drafts (
        id text PRIMARY KEY,
        conversation_id text NOT NULL
            REFERENCES assistant.conversations (id) ON DELETE CASCADE,
        draft jsonb NOT NULL,
        status text NOT NULL CHECK (status IN ('open', 'confirmed', 'cancelled')),
        idempotency_key text NOT NULL,
        created_po_id text,
        updated_at timestamptz NOT NULL
    );
    CREATE UNIQUE INDEX ux_po_drafts_one_open_per_conversation
        ON assistant.po_drafts (conversation_id) WHERE status = 'open';
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE IF EXISTS assistant.po_drafts;
    DROP TABLE IF EXISTS assistant.messages;
    DROP TABLE IF EXISTS assistant.conversations;
    """)
