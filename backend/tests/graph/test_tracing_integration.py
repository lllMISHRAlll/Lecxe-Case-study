"""A chat turn with tracing on: root run, node runs (incl. non-LLM steps) and run id storage."""

from langchain_core.tracers.base import BaseTracer
from sqlalchemy import text

from app.llm.tasks import Task
from tests.graph.conftest import PM, base_script, events_of, run


class RecordingTracer(BaseTracer):
    def __init__(self):
        super().__init__()
        self.runs = []

    def _persist_run(self, run):
        self.runs.append(run)

    def _start_trace(self, run):
        super()._start_trace(run)
        self.runs.append(run)


def test_traced_turn_records_nodes_and_stores_the_run_id(make_service, fresh_db):
    service, _, container = make_service(base_script(**{Task.ANSWER: lambda s, u: "Five."}))
    recorder = RecordingTracer()
    service.tracing.enabled = True
    service.tracing.tracer_factory = lambda run_config: recorder

    events = run(service, PM, button_id="pm_spend_by_vendor")

    names = {r.name for r in recorder.runs}
    assert "chat_turn" in names
    assert {"guard_input", "load_canned_sql", "execute_sql", "save_history"} <= names
    root = next(r for r in recorder.runs if r.name == "chat_turn")
    assert root.metadata["role"] == "procurement_manager"
    message_id = events_of(events, "done")[0]["message_id"]
    with fresh_db.read_engine.connect() as conn:
        stored = conn.execute(text("select langsmith_run_id from assistant.messages "
                                   "where id = :id"), {"id": message_id}).scalar()
    assert stored == str(root.id)
