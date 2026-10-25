from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, create_engine, select

from migrate_render_to_supabase import _copy_schema


def test_schema_copy_preserves_rows_and_foreign_key_values(tmp_path):
    source_engine = create_engine(f"sqlite:///{tmp_path / 'source.db'}")
    target_engine = create_engine(f"sqlite:///{tmp_path / 'target.db'}")
    source_metadata = MetaData()
    parents = Table(
        "parents",
        source_metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String, nullable=False),
        schema="main",
    )
    children = Table(
        "children",
        source_metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", Integer, ForeignKey("main.parents.id"), nullable=False),
        schema="main",
    )
    source_metadata.create_all(source_engine)
    with source_engine.begin() as connection:
        connection.execute(parents.insert(), {"id": 3, "name": "Preserved parent"})
        connection.execute(children.insert(), {"id": 9, "parent_id": 3})

    with target_engine.begin() as connection:
        copied = _copy_schema(source_engine, connection, "main", "main")
        assert connection.execute(select(parents.c.name)).scalar_one() == "Preserved parent"
        assert connection.execute(select(children.c.parent_id)).scalar_one() == 3

    assert copied == {"parents": 1, "children": 1}
    source_engine.dispose()
    target_engine.dispose()
