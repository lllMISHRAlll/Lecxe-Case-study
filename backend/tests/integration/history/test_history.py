"""HIS-01..07: conversations, messages and PO drafts in the assistant schema."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.core.clock import FixedClock
from app.core.errors import NotFound
from app.history.repository import DraftStatusError, HistoryRepository
from app.po.models import PODraft, POLine
from tests.fixtures.po_catalog import catalog

USER_A, USER_B = "user-a", "user-b"
NOW = datetime(2026, 11, 19, 9, 0, tzinfo=UTC)


class Clock(FixedClock):
    def tick(self):
        self._moment += timedelta(seconds=1)


@pytest.fixture
def history(fresh_db):
    return HistoryRepository(fresh_db.write_engine, clock=Clock(NOW))


def test_his_01_title_comes_from_the_first_question(history):
    conv = history.create_conversation(USER_A, "Which vendors are overdue on deliveries this "
                                               "month and by how many days exactly please?")
    assert conv.title == "Which vendors are overdue on deliveries this month and by how…"
    assert history.create_conversation(USER_A, "Spend by vendor").title == "Spend by vendor"


def test_his_02_messages_round_trip_with_payload(history):
    conv = history.create_conversation(USER_A, "Spend")
    history.add_message(conv.id, "user", "Spend by vendor")
    message_id = history.add_message(
        conv.id, "assistant", "Global leads.",
        payload={"sql": "select 1", "rows": {"rows": [["a", Decimal("1.50")]]},
                 "when": datetime(2026, 8, 1, 10, 0)},
        run_id="run-1")

    messages = history.messages(USER_A, conv.id)
    assert [(m.sender, m.text) for m in messages] == [("user", "Spend by vendor"),
                                                     ("assistant", "Global leads.")]
    assert messages[1].id == message_id
    assert messages[1].payload == {"sql": "select 1", "rows": {"rows": [["a", "1.50"]]},
                                   "when": "2026-08-01T10:00:00"}
    assert messages[1].langsmith_run_id == "run-1"


def test_his_03_users_cannot_see_each_others_conversations(history):
    conv = history.create_conversation(USER_A, "Mine")
    with pytest.raises(NotFound):
        history.messages(USER_B, conv.id)
    with pytest.raises(NotFound):
        history.delete_conversation(USER_B, conv.id)
    assert history.list_conversations(USER_B) == []


def test_his_04_soft_deleted_conversations_are_hidden(history):
    keep = history.create_conversation(USER_A, "Keep")
    gone = history.create_conversation(USER_A, "Gone")
    history.delete_conversation(USER_A, gone.id)
    assert [c.id for c in history.list_conversations(USER_A)] == [keep.id]
    with pytest.raises(NotFound):
        history.messages(USER_A, gone.id)


def test_list_is_newest_first_by_activity(history):
    first = history.create_conversation(USER_A, "First")
    history._clock.tick()
    second = history.create_conversation(USER_A, "Second")
    history._clock.tick()
    history.add_message(first.id, "user", "bump")
    assert [c.id for c in history.list_conversations(USER_A)] == [first.id, second.id]


def test_recent_turns_pairs_questions_with_answers(history):
    conv = history.create_conversation(USER_A, "Q1")
    for i in range(1, 5):
        history.add_message(conv.id, "user", f"Q{i}")
        history.add_message(conv.id, "assistant", f"A{i}")
    turns = history.recent_turns(conv.id, limit=3)
    assert [(t.question, t.answer) for t in turns] == [("Q2", "A2"), ("Q3", "A3"), ("Q4", "A4")]


def draft():
    cat = catalog()
    return PODraft(idempotency_key="key-1", vendor=cat.vendors[0], lines=[
        POLine(position=1, item=cat.items[0], quantity=Decimal("50"),
               unit_price=Decimal("120.50"))])


def test_his_05_drafts_round_trip(history):
    conv = history.create_conversation(USER_A, "PO")
    assert history.open_draft(conv.id) is None
    history.save_draft(conv.id, draft())
    loaded = history.open_draft(conv.id)
    assert loaded == draft()
    changed = loaded.model_copy(update={"payment_terms": "30 Days Credit"})
    history.save_draft(conv.id, changed)
    assert history.open_draft(conv.id).payment_terms == "30 Days Credit"


def test_his_05_status_only_moves_from_open(history):
    conv = history.create_conversation(USER_A, "PO")
    history.save_draft(conv.id, draft())
    history.close_draft(conv.id, "confirmed", created_po_id="po-1")
    assert history.open_draft(conv.id) is None
    with pytest.raises(DraftStatusError):
        history.close_draft(conv.id, "cancelled")


def test_feedback_is_stored_for_own_messages_only(history):
    conv = history.create_conversation(USER_A, "Q")
    message_id = history.add_message(conv.id, "assistant", "A", run_id="run-9")
    assert history.set_feedback(USER_A, message_id, 1) == "run-9"
    with pytest.raises(NotFound):
        history.set_feedback(USER_B, message_id, -1)


def test_his_06_migrations_only_create_objects_in_assistant(db):
    with db.read_engine.connect() as conn:
        public = {r[0] for r in conn.execute(text(
            "select table_name from information_schema.tables where table_schema = 'public'"))}
        assistant = {r[0] for r in conn.execute(text(
            "select table_name from information_schema.tables "
            "where table_schema = 'assistant'"))}
    assert len(public) == 17 and "alembic_version" not in public
    assert assistant == {"alembic_version", "conversations", "messages", "po_drafts"}


def test_his_07_migrations_downgrade_and_upgrade_cleanly(test_database):
    from app.db.migrate import downgrade, upgrade

    downgrade(test_database.url, "base")
    with test_database.handle().read_engine.connect() as conn:
        left = conn.execute(text("select count(*) from information_schema.tables "
                                 "where table_schema = 'assistant' "
                                 "and table_name <> 'alembic_version'")).scalar()
    assert left == 0
    upgrade(test_database.url)
    test_database.mark_dirty()
