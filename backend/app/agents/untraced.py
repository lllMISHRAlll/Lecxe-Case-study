"""Routers (conditional edges) without a trace run.

LangGraph traces every router call as a child of the node before it, so LangSmith shows
`_after_guard`, `_by_intent`, ... between the real steps. The next node already shows the
decision, so routers are wrapped to skip tracing.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# LangGraph's own runnable for nodes and routers; it is the only one with a `trace` switch.
from langgraph._internal._runnable import RunnableCallable


def untraced(router: Callable[..., Any]) -> RunnableCallable:
    return RunnableCallable(router, name=getattr(router, "__name__", "router"), trace=False)
