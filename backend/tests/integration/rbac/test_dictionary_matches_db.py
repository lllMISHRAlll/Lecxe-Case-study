from sqlalchemy import text

from app.auth.roles import Role
from app.rbac.scope import tables_for
from app.sql.dictionary import DICTIONARY


def db_columns(db, table):
    with db.read_engine.connect() as conn:
        rows = conn.execute(text(
            "select column_name, data_type from information_schema.columns "
            "where table_schema = 'public' and table_name = :t"), {"t": table}).all()
    return {name: dtype for name, dtype in rows}


def test_rbac_06_every_policy_table_is_documented_and_exists(raw_db):
    every_table = set().union(*(tables_for(r) for r in Role))
    assert every_table <= set(DICTIONARY)
    for table in every_table:
        documented = DICTIONARY[table].columns
        actual = db_columns(raw_db, table)
        assert set(documented) == set(actual), table
        for column, doc in documented.items():
            assert doc.type == actual[column], f"{table}.{column}"
