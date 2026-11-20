import json
from datetime import date
from decimal import Decimal

import pytest

from app.agents.events import StreamEvent
from evals.turn import ROLES, collect_turn, load_role_cases, render_rows, summarise


def ev(name, **data):
    return StreamEvent(name, data)


def test_collect_turn_joins_tokens_and_keeps_rows_and_sql():
    turn = collect_turn([
        ev("sql", sql="SELECT 1", source="generated", attempt=1),
        ev("rows", columns=[{"name": "n", "type": "int"}], rows=[[3]], row_count=1,
           truncated=False),
        ev("token", text="There are "), ev("token", text="3."),
    ])
    assert turn.answer == "There are 3."
    assert turn.sql == ["SELECT 1"]
    assert turn.rows == [[3]] and turn.columns == ["n"]


def test_answer_replace_wins_over_streamed_tokens():
    turn = collect_turn([ev("token", text="made up 99"), ev("answer_replace", text="Safe.")])
    assert turn.answer == "Safe."


def test_collect_turn_records_errors_and_no_rows():
    turn = collect_turn([ev("error", message="boom", reference="r1")])
    assert turn.error == "boom" and turn.rows is None and turn.sql == []


def test_render_rows_is_readable_and_capped():
    text = render_rows(["name", "total"], [["Zenith", Decimal("12.50")], ["Anand", 3]], limit=1)
    assert "name | total" in text and "Zenith | 12.5" in text
    assert "Anand" not in text and "1 more row" in text
    assert render_rows(["n"], []) == "No rows returned."
    assert "2026-08-01" in render_rows(["d"], [[date(2026, 8, 1)]])


def test_summarise_means_per_metric_ignoring_missing():
    results = [{"role": "a", "scores": {"match": 1.0, "faith": 0.5}},
               {"role": "a", "scores": {"match": 0.0}},
               {"role": "b", "scores": {"match": 1.0}}]
    summary = summarise(results)
    assert summary["a"] == {"cases": 2, "match": 0.5, "faith": 0.5}
    assert summary["b"] == {"cases": 1, "match": 1.0}


@pytest.mark.parametrize("role", ROLES)
def test_golden_files_are_well_formed(role):
    cases = load_role_cases(role)
    assert len(cases) >= 8
    assert len({c["id"] for c in cases}) == len(cases)
    for c in cases:
        assert c["kind"] in {"data", "refuse"}
        assert c["question"] and c["expected_answer"]
        assert (c["kind"] == "data") == bool(c.get("reference_sql")), c["id"]


def test_each_role_has_data_and_refusal_cases():
    for role in ROLES:
        assert {c["kind"] for c in load_role_cases(role)} == {"data", "refuse"}


def test_golden_files_match_the_files_on_disk():
    from evals.turn import DATASETS
    for role in ROLES:
        raw = json.loads((DATASETS / f"golden_{role}.json").read_text())
        assert all(c["id"][:2] == "".join(w[0] for w in role.split("_")) for c in raw)
