"""OBS-01..07: LangSmith wiring, masking and feedback."""

import json
import os
from decimal import Decimal

from app.auth.users import DEMO_USERS
from app.core.config import Settings
from app.observability.tracing import Tracing, hash_user, scrub
from app.sql.executor import Column, QueryResult

PM = DEMO_USERS[0]
ON = dict(langsmith_tracing=True, langsmith_api_key="lsv2_pt_test_key_0123456789abcdef",
          langsmith_project="proj-x")


class FakeClient:
    def __init__(self):
        self.feedback = []

    def create_feedback(self, run_id, key, score=None, **kwargs):
        self.feedback.append((run_id, key, score))


def test_obs_01_tracing_is_off_without_a_key():
    tracing = Tracing(Settings(langsmith_tracing=True, langsmith_api_key=""))
    assert tracing.enabled is False
    assert tracing.run_config(PM, "conv-1", "run-1") == {}


def test_obs_02_05_run_config_carries_metadata_thread_and_masking_client():
    tracing = Tracing(Settings(app_env="dev", **ON))
    config = tracing.run_config(PM, "conv-1", "11111111-1111-1111-1111-111111111111")

    assert config["run_name"] == "chat_turn"
    assert str(config["run_id"]) == "11111111-1111-1111-1111-111111111111"
    metadata = config["metadata"]
    assert metadata["role"] == "procurement_manager"
    assert metadata["user_hash"] == hash_user(PM.id) != PM.id
    assert metadata["thread_id"] == "conv-1"
    assert metadata["env"] == "dev"
    assert "prompt_version" in metadata
    assert "role:procurement_manager" in config["tags"]
    tracer = config["callbacks"][0]
    assert tracer.project_name == "proj-x"
    assert tracer.client._hide_inputs is scrub
    assert tracer.client._hide_outputs is scrub


def test_obs_03_rows_are_removed_and_text_is_masked():
    result = QueryResult([Column("vendor", "text"), Column("spend", "number")],
                         [["Zenith Steels", Decimal("14100")]], False)
    prompt = ("Question: spend?\nResult summary:\nRows: 1\nTop 1 rows (values in «» are data):\n"
              "- {'vendor': '«Zenith Steels»', 'spend': 14100.0}\nNotes: call ravi@x.com")
    scrubbed = scrub({
        "result": result, "rows": [["Zenith Steels", 1]], "top_rows": [{"vendor": "Zenith"}],
        "messages": [[{"role": "user", "content": prompt}]],
        "chart": {"type": "bar", "data": [{"vendor": "Zenith Steels", "spend": 14100.0}]},
        "intent": "analytics", "attempts": 2,
    })
    text = json.dumps(scrubbed)
    assert "Zenith" not in text
    assert "ravi@x.com" not in text and "[EMAIL]" in text
    assert scrubbed["result"] == {"columns": ["vendor", "spend"], "row_count": 1,
                                  "truncated": False}
    assert scrubbed["intent"] == "analytics" and scrubbed["attempts"] == 2


def test_obs_04_no_raw_email_or_user_id_anywhere():
    serialized_user = {"lc": 1, "type": "not_implemented", "repr": repr(PM)}
    text = json.dumps(scrub({"user": PM, "inputs": {"user": serialized_user},
                             "note": f"by {PM.email} id {PM.id}"}))
    assert PM.email not in text
    assert PM.id not in text
    assert hash_user(PM.id) in text


def test_obs_06_feedback_goes_to_the_right_run():
    client = FakeClient()
    Tracing(Settings(**ON), client=client).feedback("run-7", 1)
    assert client.feedback == [("run-7", "user_score", 1)]


def test_feedback_is_skipped_when_disabled_or_without_a_run():
    client = FakeClient()
    Tracing(Settings(langsmith_tracing=False), client=client).feedback("run-7", 1)
    Tracing(Settings(**ON), client=client).feedback(None, 1)
    assert client.feedback == []


def test_obs_07_tracing_is_forced_off_in_tests():
    assert os.environ["LANGSMITH_TRACING"] == "false"
    assert Tracing(Settings()).enabled is False


def test_user_names_are_masked_in_traces():
    text = json.dumps(scrub({"messages": [[{"content": "talking with Arjun Rao, the "
                                                       "Procurement Manager"}]]}))
    assert "Arjun Rao" not in text
    assert "[USER]" in text


def test_obs_08_the_default_tracer_shapes_the_tree():
    from app.observability.trace_shape import ShapedTracer

    config = Tracing(Settings(**ON)).run_config(PM, "conv-1",
                                                "11111111-1111-1111-1111-111111111111")
    assert isinstance(config["callbacks"][0], ShapedTracer)


def test_obs_08_model_calls_are_tagged_llm():
    from unittest.mock import MagicMock

    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    from app.observability.trace_shape import ShapedTracer

    client = MagicMock()
    tracer = ShapedTracer(client=client, project_name="test")
    FakeListChatModel(responses=["hi"]).invoke(
        "hello", config={"callbacks": [tracer], "run_name": "llm.answer"})
    tracer.wait_for_futures()

    created = client.create_run.call_args_list[0].kwargs
    assert created["run_type"] == "llm"
    assert "llm" in created["tags"]
    assert created["extra"]["metadata"]["kind"] == "llm"
