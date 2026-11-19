"""Validates SQL written by the LLM before it may run.

Checks run in a fixed order (CHECK_ORDER) and the first failure is reported, so the fix step
gets one clear error to work from. Rules:

* exactly one SELECT (or WITH ... SELECT, or a set operation of SELECTs)
* no comments, no SELECT INTO, no row locking, no SELECT *
* only tables in the role's scope, wherever they appear (joins, subqueries, CTEs, unions)
* only allowlisted functions
* a LIMIT no higher than the row cap
"""

from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, TokenError
from sqlglot.tokens import Tokenizer

from app.auth.roles import Role
from app.rbac.scope import can_access_table

MAX_LENGTH = 10_000

CHECK_ORDER = ("length", "comments", "parse", "single_statement", "statement_type", "clauses",
               "star", "tables", "functions", "limit")

# sqlglot expression classes that are safe to evaluate.
ALLOWED_FUNCTION_CLASSES = frozenset({
    # aggregates and windows
    "Avg", "Count", "Sum", "Min", "Max", "ArrayAgg", "GroupConcat", "Stddev", "StddevPop",
    "StddevSamp", "Variance", "VariancePop", "PercentileCont", "PercentileDisc", "Median",
    "RowNumber", "Rank", "DenseRank", "Ntile", "Lag", "Lead", "FirstValue", "LastValue",
    "LogicalAnd", "LogicalOr",
    # conditionals and casts
    "Case", "If", "Coalesce", "Nullif", "Cast", "TryCast", "Greatest", "Least",
    # numbers
    "Abs", "Ceil", "Floor", "Round", "Mod", "Pow", "Sqrt", "Sign", "Div",
    # text
    "Concat", "ConcatWs", "Lower", "Upper", "Trim", "Length", "Substring", "Initcap", "Left",
    "Right", "StrPosition", "SplitPart", "Pad", "Replace", "RegexpReplace", "RegexpLike",
    # dates
    "Extract", "CurrentDate", "CurrentTimestamp", "TimestampTrunc", "DateTrunc", "TimeToStr",
    "StrToDate", "StrToTime", "DateDiff", "DateAdd", "DateSub", "TsOrDsToDate", "ToChar",
    # json
    "JSONExtract", "JSONExtractScalar", "JSONBExtract", "JSONBExtractScalar", "JSONArrayLength",
    # boolean connectors and predicates that sqlglot models as functions
    "And", "Or", "Not", "Exists", "Xor",
})

# Functions sqlglot doesn't model, allowed by name.
ALLOWED_FUNCTION_NAMES = frozenset({
    "age", "date_part", "to_char", "to_date", "initcap", "split_part", "btrim", "ltrim",
    "rtrim", "string_agg", "array_agg", "json_array_length", "jsonb_array_length",
    "json_array_elements_text", "jsonb_array_elements_text", "json_typeof", "jsonb_typeof",
    "bool_and", "bool_or", "every", "now", "make_date", "date",
})

_FORBIDDEN_NODES = tuple(
    getattr(exp, name) for name in (
        "Insert", "Update", "Delete", "Merge", "Create", "Drop", "Alter", "AlterTable",
        "TruncateTable", "Command", "Copy", "Grant", "Revoke", "Comment", "Set", "Use",
        "Transaction", "Commit", "Rollback", "Pragma", "LoadData", "Analyze",
    ) if hasattr(exp, name)
)
_QUERY_ROOTS = tuple(getattr(exp, n) for n in ("Select", "Union", "Except", "Intersect",
                                               "SetOperation") if hasattr(exp, n))


class SqlRejectedError(ValueError):
    def __init__(self, check: str, message: str) -> None:
        super().__init__(message)
        self.check = check


@dataclass(frozen=True)
class ValidatedSql:
    sql: str
    tables: frozenset[str]


class SqlValidator:
    def __init__(self, *, row_cap: int) -> None:
        self._row_cap = row_cap

    def validate(self, sql: str, role: Role) -> ValidatedSql:
        sql = sql.strip().rstrip(";").strip()
        self._check_length(sql)
        self._check_comments(sql)
        tree = self._parse_single(sql)
        self._check_statement_type(tree)
        self._check_clauses(tree)
        self._check_star(tree)
        tables = self._check_tables(tree, role)
        self._check_functions(tree)
        self._apply_limit(tree)
        return ValidatedSql(sql=tree.sql(dialect="postgres"), tables=frozenset(tables))

    # ------------------------------------------------------------------ checks

    def _check_length(self, sql: str) -> None:
        if not sql:
            raise SqlRejectedError("length", "The query is empty.")
        if len(sql) > MAX_LENGTH:
            raise SqlRejectedError("length", "The query is too long.")

    def _check_comments(self, sql: str) -> None:
        try:
            tokens = Tokenizer().tokenize(sql)
        except TokenError as exc:
            raise SqlRejectedError("parse", "The query could not be parsed.") from exc
        if any(t.comments for t in tokens) or "--" in _outside_strings(tokens) or \
                "/*" in _outside_strings(tokens):
            raise SqlRejectedError("comments", "Comments are not allowed in queries.")

    def _parse_single(self, sql: str) -> exp.Expression:
        try:
            statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
        except (ParseError, TokenError) as exc:
            raise SqlRejectedError("parse", "The query could not be parsed.") from exc
        if len(statements) != 1:
            raise SqlRejectedError("single_statement", "Exactly one statement is allowed.")
        return statements[0]

    def _check_statement_type(self, tree: exp.Expression) -> None:
        if not isinstance(tree, _QUERY_ROOTS) or any(
                isinstance(node, _FORBIDDEN_NODES) for node in tree.walk()):
            raise SqlRejectedError("statement_type", "Only SELECT queries are allowed.")

    def _check_clauses(self, tree: exp.Expression) -> None:
        if tree.find(exp.Into):
            raise SqlRejectedError("clauses", "SELECT INTO is not allowed.")
        if tree.find(exp.Placeholder) or tree.find(exp.Parameter):
            raise SqlRejectedError("clauses", "Bind parameters are not allowed. Write literal "
                                              "values, e.g. DATE '2026-11-19'.")
        if any(s.args.get("locks") for s in tree.find_all(exp.Select)):
            raise SqlRejectedError("clauses",
                                   "Row locking (FOR UPDATE / FOR SHARE) is not allowed.")

    def _check_star(self, tree: exp.Expression) -> None:
        for select in tree.find_all(exp.Select):
            for projection in select.expressions:
                if isinstance(projection, exp.Star) or (
                        isinstance(projection, exp.Column) and isinstance(projection.this,
                                                                          exp.Star)):
                    raise SqlRejectedError(
                        "star", "SELECT * is not allowed. Name the columns you need.")

    def _check_tables(self, tree: exp.Expression, role: Role) -> set[str]:
        cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
        used: set[str] = set()
        for table in tree.find_all(exp.Table):
            if isinstance(table.this, exp.Func):
                continue  # table-valued function, checked by the function allowlist
            parts = [p for p in (table.catalog, table.db, table.name) if p]
            name = ".".join(parts).lower()
            if len(parts) == 1 and name in cte_names:
                continue
            if not can_access_table(role, name):
                raise SqlRejectedError("tables", f"Table {name} is not available to your role.")
            used.add(name.removeprefix("public."))
        return used

    def _check_functions(self, tree: exp.Expression) -> None:
        for func in tree.find_all(exp.Func):
            if isinstance(func, exp.Anonymous):
                name = str(func.this).lower()
                if name not in ALLOWED_FUNCTION_NAMES:
                    raise SqlRejectedError("functions", f"Function {name} is not allowed.")
            elif type(func).__name__ not in ALLOWED_FUNCTION_CLASSES:
                raise SqlRejectedError("functions",
                                       f"Function {func.sql_name().lower()} is not allowed.")

    def _apply_limit(self, tree: exp.Expression) -> None:
        limit = tree.args.get("limit")
        value = None
        if isinstance(limit, exp.Limit) and isinstance(limit.expression, exp.Literal):
            try:
                value = int(limit.expression.this)
            except ValueError:
                value = None
        if value is None or value > self._row_cap:
            tree.set("limit", exp.Limit(expression=exp.Literal.number(self._row_cap)))


def _outside_strings(tokens) -> str:
    from sqlglot.tokens import TokenType

    return " ".join(t.text for t in tokens if t.token_type not in (TokenType.STRING,
                                                                     TokenType.NATIONAL_STRING))
