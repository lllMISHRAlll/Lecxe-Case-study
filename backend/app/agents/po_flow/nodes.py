"""PO subgraph nodes. Each user turn ends after a question, the confirmation card or a result.

The draft lives in assistant.po_drafts between turns. Writing the PO uses PORepository only:
no LLM-written SQL ever reaches this path.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from app.agents.deps import GraphDeps
from app.agents.events import emit, step
from app.agents.prompts.po import PO_EXTRACT_SYSTEM
from app.agents.state import AgentState
from app.domain.vocabulary import CANONICAL_TERMS, CANONICAL_UNITS
from app.llm.tasks import Task
from app.po.models import PODraft, fmt_money
from app.po.repository import POCreateError
from app.po.resolver import EntityResolver
from app.po.rules import apply_defaults, next_question, review, suggest_prices
from app.po.slots import SlotExtraction, Unresolved, apply_choice, merge_extraction

VENDOR_BUTTONS = 8
NO_DRAFT = "There's no open PO draft in this conversation. Tell me what you'd like to order."


def _symbol(currency: str) -> str:
    return "₹" if currency == "INR" else "$"


def _describe_line(ln: Any) -> str:
    name = ln.item.name if ln.item else "?"
    code = ln.item.code if ln.item else "?"
    unit = ln.unit or (ln.item.unit if ln.item else "?")
    qty = ln.quantity if ln.quantity is not None else "?"
    price = ln.unit_price if ln.unit_price is not None else "?"
    return f"  line {ln.position}: {name} ({code}), unit {unit}, qty {qty}, unit price {price}"


def describe(draft: PODraft) -> str:
    """The draft as the extractor sees it: numbered lines and the last question asked."""
    vendor = draft.vendor.name if draft.vendor else "not chosen"
    lines = "\n".join(_describe_line(ln) for ln in draft.lines)
    return (
        f"Vendor: {vendor}\nLines:\n{lines or '  none yet'}\nCurrency: {draft.currency}\n"
        f"Payment terms: {draft.payment_terms or 'not set'}\n"
        f"Last question: {draft.last_question or 'none'}"
    )


class PONodes:
    def __init__(self, deps: GraphDeps) -> None:
        self.d = deps

    # ------------------------------------------------------------------ load and route

    def load_draft(self, state: AgentState) -> dict[str, Any]:
        draft = self.d.history.open_draft(state["conversation_id"])
        step("load_draft", "Opened the PO draft" if draft else "Starting a PO draft")
        return {"po_draft": draft, "po_unresolved": [], "po_notes": []}

    @staticmethod
    def action(state: AgentState) -> str:
        command = state.get("po_command") or (state.get("po_action") or {}).get("type")
        if command in ("confirm", "cancel", "choose"):
            return command if state.get("po_draft") else "no_draft"
        return "extract"

    # ------------------------------------------------------------------ fill the draft

    def extract_slots(self, state: AgentState) -> dict[str, Any]:
        draft = state.get("po_draft") or PODraft(idempotency_key=str(uuid.uuid4()))
        extraction = self.d.llm.structured(
            Task.PO_EXTRACT,
            schema=SlotExtraction,
            user=state["question"],
            system=PO_EXTRACT_SYSTEM.format(
                today=self.d.clock.today().isoformat(),
                units=", ".join(sorted(CANONICAL_UNITS)),
                terms="; ".join(CANONICAL_TERMS),
                draft=describe(draft),
            ),
        )
        resolver = EntityResolver(self.d.load_catalog())
        draft, unresolved = merge_extraction(draft, extraction, resolver)
        step("extract_slots", "Read the order details")
        return {"po_draft": draft, "po_unresolved": unresolved}

    def choose(self, state: AgentState) -> dict[str, Any]:
        draft = state["po_draft"]
        assert draft is not None
        kind, _, choice_id = str((state.get("po_action") or {}).get("choice", "")).partition(":")
        pending = (draft.pending or {}).get("pending", {}) if draft.pending else {}
        try:
            draft = apply_choice(
                draft,
                kind,
                choice_id,
                self.d.load_catalog(),
                **{k: Decimal(v) if k != "unit" else v for k, v in pending.items()},
            )
        except StopIteration:
            return {"po_notes": ["That option is no longer available."]}
        draft.pending = None
        step("choose", "Applied your choice")
        return {"po_draft": draft}

    def review_draft(self, state: AgentState) -> dict[str, Any]:
        draft = state["po_draft"]
        assert draft is not None
        draft = suggest_prices(apply_defaults(draft, self.d.clock.today()), self.d.load_catalog())
        step("validate_draft", "Checked the draft")
        return {"po_draft": draft}

    @staticmethod
    def after_review(state: AgentState) -> str:
        unresolved: list[Unresolved] = state.get("po_unresolved") or []
        if any(u.kind != "invalid" for u in unresolved):
            return "ask_choice"
        draft = state["po_draft"]
        assert draft is not None
        return "show_confirmation" if review(draft).complete else "ask_next_slot"

    # ------------------------------------------------------------------ ask the user

    def ask_choice(self, state: AgentState) -> dict[str, Any]:
        draft = state["po_draft"]
        assert draft is not None
        first = next(u for u in state["po_unresolved"] if u.kind != "invalid")
        if not first.choices:
            reply = (
                f"I couldn't find a {first.kind} matching '{first.query}'. Could you give "
                "the exact name" + (" or item code?" if first.kind == "item" else "?")
            )
        else:
            reply = f"Which {first.kind} did you mean by '{first.query}'?"
            draft.pending = {"kind": first.kind, "pending": first.pending}
            emit(
                "choices",
                {
                    "prompt": reply,
                    "options": [
                        {"id": f"{first.kind}:{o.id}", "label": o.label} for o in first.choices
                    ],
                },
            )
        draft.last_question = reply
        return {"po_draft": draft, "reply": self._with_notes(state, reply)}

    def ask_next_slot(self, state: AgentState) -> dict[str, Any]:
        draft = state["po_draft"]
        assert draft is not None
        question = next_question(review(draft))
        assert question is not None
        options = [(o.id, o.label) for o in question.options]
        if question.slot == "vendor":
            options = [(v.id, v.name) for v in self.d.load_catalog().recent_vendors(VENDOR_BUTTONS)]
        if options:
            emit(
                "choices",
                {
                    "prompt": question.text,
                    "options": [
                        {"id": f"{question.slot}:{oid}", "label": label} for oid, label in options
                    ],
                },
            )
        draft.last_question = question.text
        return {"po_draft": draft, "reply": self._with_notes(state, question.text)}

    def show_confirmation(self, state: AgentState) -> dict[str, Any]:
        draft = state["po_draft"]
        assert draft is not None and draft.vendor is not None
        rev = review(draft)
        contract = draft.to_contract(rev)
        emit("po_draft", {"draft": contract})
        total = f"{_symbol(draft.currency)}{contract['total_amount']}"
        reply = (
            f"Here's the PO for {draft.vendor.name}, {len(draft.lines)} line(s), total "
            f"{total} with {draft.payment_terms}. Press Confirm to raise it, or tell me "
            "what to change."
        )
        return {"reply": self._with_notes(state, reply), "payload": {"po_draft": contract}}

    def _with_notes(self, state: AgentState, text: str) -> str:
        notes = [u.query for u in state.get("po_unresolved") or [] if u.kind == "invalid"]
        notes += state.get("po_notes") or []
        return " ".join([*notes, text])

    def save_draft(self, state: AgentState) -> dict[str, Any]:
        draft = state.get("po_draft")
        if draft is not None and draft.status == "open":
            self.d.history.save_draft(state["conversation_id"], draft)
        return {"reply_mode": "text"}

    # ------------------------------------------------------------------ finish

    def insert_po(self, state: AgentState) -> dict[str, Any]:
        draft = state["po_draft"]
        assert draft is not None
        draft = suggest_prices(apply_defaults(draft, self.d.clock.today()), self.d.load_catalog())
        try:
            created = self.d.po_repo.create(draft, state["user"])
        except POCreateError as exc:
            step("insert_po", "Couldn't save the PO", "error")
            return {"reply": f"The PO wasn't saved. {exc}", "reply_mode": "text", "po_draft": draft}
        self.d.history.close_draft(
            state["conversation_id"], "confirmed", created_po_id=created.po_id
        )
        result = {
            "po_number": created.po_number,
            "po_id": created.po_id,
            "total_amount": fmt_money(created.total_amount),
            "currency": created.currency,
        }
        emit("po_created", result)
        step("insert_po", "Raised the PO")
        vendor = draft.vendor.name if draft.vendor else "the vendor"
        reply = (
            f"Done. **{created.po_number}** is raised with {vendor} for "
            f"{_symbol(created.currency)}{result['total_amount']}."
        )
        closed = draft.model_copy(update={"status": "confirmed"})
        return {
            "reply": reply,
            "reply_mode": "text",
            "po_draft": closed,
            "payload": {"po_created": result},
        }

    def cancel(self, state: AgentState) -> dict[str, Any]:
        self.d.history.close_draft(state["conversation_id"], "cancelled")
        step("cancel_draft", "Cancelled the draft")
        draft = state["po_draft"]
        closed = draft.model_copy(update={"status": "cancelled"}) if draft else None
        return {
            "reply": "Cancelled the PO draft. Nothing was saved.",
            "reply_mode": "text",
            "po_draft": closed,
        }

    @staticmethod
    def no_draft(state: AgentState) -> dict[str, Any]:
        return {"reply": NO_DRAFT, "reply_mode": "text"}
