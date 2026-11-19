"""Everything the graph nodes need, built once from the container."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.agents.routing.rewriter import FollowUpRewriter
from app.agents.routing.router import IntentRouter
from app.core.clock import Clock
from app.core.config import Settings
from app.guardrails.injection import InjectionDetector
from app.history.repository import HistoryRepository
from app.llm.port import LLM
from app.po.catalog import Catalog
from app.po.repository import PORepository
from app.sql.canned.base import Registry
from app.sql.executor import QueryExecutor
from app.sql.explain import SqlExplainer
from app.sql.validator import SqlValidator
from app.viz.chart_rules import ChartDecider


@dataclass
class GraphDeps:
    settings: Settings
    clock: Clock
    llm: LLM
    guard: InjectionDetector
    rewriter: FollowUpRewriter
    router: IntentRouter
    registry: Registry
    executor: QueryExecutor
    validator: SqlValidator
    explainer: SqlExplainer
    charts: ChartDecider
    history: HistoryRepository
    po_repo: PORepository
    load_catalog: Callable[[], Catalog]
