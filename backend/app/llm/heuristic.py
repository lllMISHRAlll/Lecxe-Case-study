"""Offline stand-in for OpenAI, used when FAKE_LLM=1 or no API key is set.

Deterministic and rule-based, good enough to demo and to drive end-to-end tests: it maps
questions to the role's saved queries and reads simple PO requests with regular expressions.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from app.llm.port import T
from app.llm.tasks import Task
from app.sql.canned import REGISTRY

_KEYWORDS = [
    (("overdue", "late"), "pm_overdue"), (("open po", "open purchase"), "pm_open_pos"),
    (("spend", "vendor"), "pm_spend_by_vendor"), (("fulfil",), "pm_fulfilment"),
    (("unexpected", "unplanned"), "pm_unexpected_receipts"), (("block", "payment"),
                                                              "pm_blocking_payments"),
    (("out of stock",), "pm_out_of_stock_in_use"), (("category",), "bo_spend_by_category"),
    (("pipeline", "status"), "bo_po_pipeline"), (("scorecard",), "bo_vendor_scorecard"),
    (("week", "in vs out"), "bo_stock_in_out_weekly"), (("warehouse", "stock"),
                                                         "wm_stock_by_warehouse"),
    (("inbound", "expected"), "wm_expected_inbound"), (("movement",), "wm_recent_movements"),
    (("consumption", "issued"), "wm_consumption_by_target"),
]
_PO = re.compile(r"(?:for\s+)?(?P<qty>\d+(?:\.\d+)?)\s+(?P<item>.+?)\s+from\s+(?P<vendor>.+?)"
                 r"(?:\s+at\s+(?P<price>\d+(?:\.\d+)?))?(?:\s+each)?\s*$", re.I)
_TERMS = re.compile(r"\b(days?|advance|dispatch|credit|pdc|against)\b", re.I)
_QTY_PRICE = re.compile(r"(?P<qty>\d+(?:\.\d+)?)\s+(?:at|@)\s+(?P<price>\d+(?:\.\d+)?)", re.I)


def _literal(sql: str) -> str:
    """Generated SQL runs without bind parameters, so inline them."""
    return sql.replace("CAST(:today AS date)", "CURRENT_DATE").replace("CAST(:fx AS numeric)",
                                                                       "88")


def _sql_for(question: str) -> str:
    q = question.lower()
    for words, button in _KEYWORDS:
        if any(w in q for w in words):
            return _literal(REGISTRY.get(button).sql)
    return _literal(REGISTRY.get("pm_open_pos").sql)


class HeuristicLLM:
    def structured(self, task: Task, *, system: str, user: str, schema: type[T]) -> T:
        if task is Task.GUARD:
            return schema.model_validate({"allowed": True, "category": "ok"})
        if task is Task.ROUTE:
            return schema.model_validate({"intent": "analytics", "confidence": 0.9})
        if task is Task.REWRITE:
            return schema.model_validate({"question": user.rsplit("Latest message: ", 1)[-1]})
        if task is Task.SCHEMA_LINK:
            tables = re.findall(r"^- (\w+):", user, re.M)
            return schema.model_validate({"answerable": True, "tables": tables})
        if task is Task.CHART:
            return schema.model_validate({"type": "table"})
        if task is Task.PO_EXTRACT:
            return schema.model_validate(self._po(user))
        raise ValueError(f"No heuristic for {task}")

    def _po(self, text: str) -> dict:
        text = re.sub(r"^(please\s+)?(raise|create|make|place|draft)\s+(a\s+)?(new\s+)?"
                      r"(po|purchase order)\s*", "", text.strip(), flags=re.I)
        if match := _PO.search(text):
            line = {"item": match["item"], "quantity": float(match["qty"])}
            if match["price"]:
                line["unit_price"] = float(match["price"])
            return {"vendor": match["vendor"], "lines": [line]}
        if _TERMS.search(text):
            return {"payment_terms": text}
        if match := _QTY_PRICE.search(text):
            return {"lines": [{"action": "update", "quantity": float(match["qty"]),
                               "unit_price": float(match["price"])}]}
        if numbers := re.findall(r"\d+(?:\.\d+)?", text):
            return {"lines": [{"action": "update", "unit_price": float(numbers[-1])}]}
        return {"payment_terms": text} if text else {}

    def text(self, task: Task, *, system: str, user: str) -> str:
        if task in (Task.GENERATE_SQL, Task.FIX_SQL):
            question = re.search(r"Question: (.*)", user)
            return _sql_for(question.group(1) if question else user)
        if task is Task.ANSWER:
            rows = re.search(r"Rows: (\d+)", user)
            count = rows.group(1) if rows else "0"
            return f"Here are the results: **{count} rows**. See the table and chart for details."
        if task is Task.CHAT_REPLY:
            return ("Hi! I can answer questions about vendors, purchase orders, payments, "
                    "receipts and stock. Try one of the suggested questions.")
        raise ValueError(f"No heuristic for {task}")

    def stream(self, task: Task, *, system: str, user: str) -> Iterator[str]:
        yield from re.findall(r"\S+\s*", self.text(task, system=system, user=user))
