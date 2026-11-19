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
        """The LLM selected by LLM_PROVIDER, wrapped with one retry for unusable output."""
        from app.llm.retry import RetryingLLM

        if self.llm is not None:
            return RetryingLLM(self.llm)
        return RetryingLLM(self._select_llm())

    def _select_llm(self) -> LLM:
        from app.llm.heuristic import HeuristicLLM

        s = self.settings
        provider = s.llm_provider
        key = (s.anthropic_api_key if provider == "anthropic" else s.openai_api_key)
        key_value = key.get_secret_value()
        if s.fake_llm:
            log.warning("FAKE_LLM is set: using the offline heuristic LLM")
            return HeuristicLLM()
        if not key_value:
            log.warning("No %s_API_KEY set for LLM_PROVIDER=%s: using the offline heuristic "
                        "LLM", provider.upper(), provider)
            return HeuristicLLM()
        if provider == "anthropic":
            from app.llm.anthropic_llm import AnthropicLLM

            if not key_value.startswith("sk-ant-"):
                log.error("ANTHROPIC_API_KEY doesn't look like an Anthropic key (sk-ant-...). "
                          "Anthropic will reject it.")
            return AnthropicLLM(api_key=key_value, fast_model=s.anthropic_model_fast,
                                strong_model=s.anthropic_model_strong, trace=self._llm_tracer())
        from app.llm.openai_llm import OpenAILLM

        if key_value.startswith("sk-ant-"):
            log.error("OPENAI_API_KEY looks like an Anthropic key (sk-ant-...). OpenAI will "
                      "reject it: set an OpenAI key (sk-... or sk-proj-...), or set "
                      "LLM_PROVIDER=anthropic and ANTHROPIC_API_KEY.")
        return OpenAILLM(api_key=key_value, fast_model=s.openai_model_fast,
                         strong_model=s.openai_model_sql)

    def _llm_tracer(self):
        """Wraps SDK calls as LangSmith LLM runs (masked) when tracing is on."""
        if not self.tracing.enabled:
            return None
        from langsmith import traceable

        from app.observability.tracing import scrub

        client = self.tracing.client

        def trace(name, fn):
            return traceable(run_type="llm", name=name, client=client,
                             process_inputs=scrub, process_outputs=scrub, tags=["llm"],
                             metadata={"ls_provider": "anthropic", "kind": "llm"})(fn)

        return trace

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
            load_catalog=lambda: DbCatalog.load(db.read_engine), tracing=self.tracing)

    @cached_property
    def tracing(self):
        from app.observability.tracing import Tracing

        return Tracing(self.settings)

    def feedback_sink(self, run_id: str | None, score: int) -> None:
        """Forwards a thumbs up or down to LangSmith when tracing is on."""
        self.tracing.feedback(run_id, score)

    @cached_property
    def chat_service(self):
        from app.agents.service import ChatService

        return ChatService(self.graph_deps)
