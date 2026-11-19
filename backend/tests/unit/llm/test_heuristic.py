"""The offline LLM used for demos without an API key and for end-to-end tests."""

import pytest

from app.agents.routing.rewriter import Rewritten
from app.agents.routing.router import RouteClassification
from app.agents.sql_agent.nodes import LinkedSchema
from app.guardrails.injection import GuardDecision
from app.llm.heuristic import HeuristicLLM
from app.llm.tasks import Task
from app.po.slots import SlotExtraction
from app.sql.canned import REGISTRY
from app.viz.chart_rules import ChartChoice

llm = HeuristicLLM()


def test_structured_tasks():
    assert llm.structured(Task.GUARD, system="", user="x", schema=GuardDecision).allowed
    assert llm.structured(Task.ROUTE, system="", user="x",
                          schema=RouteClassification).intent == "analytics"
    assert llm.structured(Task.REWRITE, system="", user="Earlier\nLatest message: and July?",
                          schema=Rewritten).question == "and July?"
    linked = llm.structured(Task.SCHEMA_LINK, system="", schema=LinkedSchema,
                            user="Tables:\n- proc_vendors: x\n- inv_items: y\n\nQuestion: q")
    assert linked.tables == ["proc_vendors", "inv_items"]
    assert llm.structured(Task.CHART, system="", user="", schema=ChartChoice).type == "table"


@pytest.mark.parametrize(("text", "expected"), [
    ("Raise a PO for 50 MS Tube 25x40 from Zenith Steels at 120 each",
     {"vendor": "Zenith Steels", "lines": [{"item": "MS Tube 25x40", "quantity": 50.0,
                                             "unit_price": 120.0}]}),
    ("create a purchase order for 10 relays from Anand",
     {"vendor": "Anand", "lines": [{"item": "relays", "quantity": 10.0}]}),
    ("50 at 120", {"lines": [{"action": "update", "quantity": 50.0, "unit_price": 120.0}]}),
    ("make it 115", {"lines": [{"action": "update", "unit_price": 115.0}]}),
    ("30 Days Credit", {"payment_terms": "30 Days Credit"}),
])
def test_po_extraction(text, expected):
    got = llm.structured(Task.PO_EXTRACT, system="", user=text, schema=SlotExtraction)
    assert got.model_dump(exclude_none=True, exclude_defaults=True) == SlotExtraction(
        **expected).model_dump(exclude_none=True, exclude_defaults=True)


@pytest.mark.parametrize(("question", "button"), [
    ("Which deliveries are overdue?", "pm_overdue"), ("spend by vendor", "pm_spend_by_vendor"),
    ("stock in each warehouse", "wm_stock_by_warehouse"), ("something else", "pm_open_pos"),
])
def test_sql_maps_questions_to_saved_queries(question, button):
    sql = llm.text(Task.GENERATE_SQL, system="", user=f"Schema...\nQuestion: {question}\nSQL:")
    expected = REGISTRY.get(button).sql.replace("CAST(:today AS date)", "CURRENT_DATE")
    assert sql == expected.replace("CAST(:fx AS numeric)", "88")
    assert ":today" not in sql and ":fx" not in sql


def test_answer_chat_and_stream():
    assert "**3 rows**" in llm.text(Task.ANSWER, system="", user="Rows: 3\nColumns: a")
    assert llm.text(Task.CHAT_REPLY, system="", user="hi").startswith("Hi!")
    assert "".join(llm.stream(Task.ANSWER, system="", user="Rows: 2")).startswith("Here are")


def test_unknown_tasks_raise():
    with pytest.raises(ValueError):
        llm.text(Task.GUARD, system="", user="")
    with pytest.raises(ValueError):
        llm.structured(Task.ANSWER, system="", user="", schema=ChartChoice)
