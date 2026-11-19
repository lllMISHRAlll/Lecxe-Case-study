"""Builds and holds the app's collaborators. Routes and graph nodes get them from here."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import cached_property

from app.api.rate_limit import RateLimiter
from app.auth.tokens import TokenService
from app.auth.users import UserDirectory
from app.core.clock import Clock, SystemClock
from app.core.config import Settings
from app.db.sessions import Database
from app.llm.port import LLM

log = logging.getLogger(__name__)


@dataclass
class Container:
    settings: Settings
    clock: Clock = field(default_factory=SystemClock)
    users: UserDirectory = field(default_factory=UserDirectory)
    db: Database | None = None
    llm: LLM | None = None

    def __post_init__(self) -> None:
        self.tokens = TokenService(
            secret=self.settings.jwt_secret.get_secret_value(),
            ttl_hours=self.settings.jwt_ttl_hours,
            clock=self.clock,
        )
        self.limiter = RateLimiter(self.clock)

    @cached_property
    def database(self) -> Database:
        if self.db is not None:
            return self.db
        return Database.connect(self.settings.database_url.get_secret_value(),
                                sslmode=self.settings.database_sslmode,
                                statement_timeout_ms=self.settings.statement_timeout_ms)

    @cached_property
    def language_model(self) -> LLM:
        from app.llm.retry import RetryingLLM

        if self.llm is not None:
            return RetryingLLM(self.llm)
        key = self.settings.openai_api_key.get_secret_value()
        if self.settings.fake_llm or not key:
            from app.llm.heuristic import HeuristicLLM

            log.warning("Using the offline heuristic LLM (FAKE_LLM set or no OPENAI_API_KEY)")
            return RetryingLLM(HeuristicLLM())
        from app.llm.openai_llm import OpenAILLM

        return RetryingLLM(OpenAILLM(api_key=key, fast_model=self.settings.openai_model_fast,
                                     strong_model=self.settings.openai_model_sql))

    @cached_property
    def history(self):
        from app.history.repository import HistoryRepository

        return HistoryRepository(self.database.write_engine, clock=self.clock)

    @cached_property
    def graph_deps(self):
        from app.agents.deps import GraphDeps
        from app.agents.routing.rewriter import FollowUpRewriter
        from app.agents.routing.router import IntentRouter
        from app.guardrails.injection import InjectionDetector
        from app.po.catalog_db import DbCatalog
        from app.po.repository import PORepository
        from app.sql.canned import REGISTRY
        from app.sql.executor import QueryExecutor
        from app.sql.explain import SqlExplainer
        from app.sql.validator import SqlValidator
        from app.viz.chart_rules import ChartDecider

        db, llm, s = self.database, self.language_model, self.settings
        return GraphDeps(
            settings=s, clock=self.clock, llm=llm, guard=InjectionDetector(llm),
            rewriter=FollowUpRewriter(llm), router=IntentRouter(llm), registry=REGISTRY,
            executor=QueryExecutor(db.read_engine, row_cap=s.row_cap),
            validator=SqlValidator(row_cap=s.row_cap),
            explainer=SqlExplainer(db.read_engine, cost_limit=s.explain_cost_limit),
            charts=ChartDecider(llm), history=self.history,
            po_repo=PORepository(db.write_engine, clock=self.clock),
            load_catalog=lambda: DbCatalog.load(db.read_engine))

    def feedback_sink(self, run_id: str | None, score: int) -> None:
        """Forwards a thumbs up or down to LangSmith when tracing is on."""

    @cached_property
    def chat_service(self):
        from app.agents.service import ChatService

        return ChatService(self.graph_deps)
