"""Copy the Render PostgreSQL application and LMS schemas into one Supabase database."""

import os
from sqlalchemy import Integer, MetaData, Table, create_engine, inspect, select, text
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.engine import Connection, Engine

BATCH_SIZE = 1000


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Set {name} before running this migration.")
    return value


def _copy_schema(
    source_engine: Engine,
    target_connection: Connection,
    source_schema: str,
    target_schema: str,
) -> dict[str, int]:
    source_metadata = MetaData()
    source_metadata.reflect(bind=source_engine, schema=source_schema)
    target_metadata = MetaData()

    def remap_foreign_key_schema(
        table: Table,
        to_schema: str | None,
        constraint: ForeignKeyConstraint,
        referred_schema: str | None,
    ) -> str | None:
        del table, to_schema, constraint
        if referred_schema in {None, source_schema}:
            return target_schema
        return referred_schema

    for table in source_metadata.sorted_tables:
        table.to_metadata(
            target_metadata,
            schema=target_schema,
            referred_schema_fn=remap_foreign_key_schema,
        )
    target_metadata.create_all(bind=target_connection)

    copied: dict[str, int] = {}
    with source_engine.connect() as source_connection:
        for source_table in source_metadata.sorted_tables:
            target_table = target_metadata.tables[f"{target_schema}.{source_table.name}"]
            result = source_connection.execute(select(source_table))
            table_count = 0
            while rows := result.fetchmany(BATCH_SIZE):
                target_connection.execute(target_table.insert(), [dict(row._mapping) for row in rows])
                table_count += len(rows)
            copied[source_table.name] = table_count
    return copied


def _reset_sequences(connection: Connection, schema: str) -> None:
    preparer = connection.dialect.identifier_preparer
    for table in inspect(connection).get_table_names(schema=schema):
        qualified_table = f"{schema}.{table}"
        quoted_table = f"{preparer.quote_schema(schema)}.{preparer.quote(table)}"
        columns = inspect(connection).get_columns(table, schema=schema)
        for column in columns:
            if not isinstance(column["type"], Integer):
                continue
            sequence_name = connection.scalar(
                text("SELECT pg_get_serial_sequence(:table_name, :column_name)"),
                {"table_name": qualified_table, "column_name": column["name"]},
            )
            if not sequence_name:
                continue
            quoted_column = preparer.quote(column["name"])
            connection.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence(:table_name, :column_name), "
                    f"COALESCE(MAX({quoted_column}), 1), MAX({quoted_column}) IS NOT NULL) "
                    f"FROM {quoted_table}"
                ),
                {"table_name": qualified_table, "column_name": column["name"]},
            )


def main() -> None:
    source_app_engine = create_engine(_required_env("SOURCE_APP_DATABASE_URL"))
    source_lms_engine = create_engine(_required_env("SOURCE_LMS_DATABASE_URL"))
    target_engine = create_engine(_required_env("SUPABASE_DATABASE_URL"))

    if any(
        engine.dialect.name != "postgresql"
        for engine in (source_app_engine, source_lms_engine, target_engine)
    ):
        raise RuntimeError("The source and destination connections must all use PostgreSQL.")

    try:
        with target_engine.begin() as target_connection:
            target_connection.execute(text("CREATE SCHEMA IF NOT EXISTS mock_lms"))
            app_counts = _copy_schema(source_app_engine, target_connection, "public", "public")
            lms_counts = _copy_schema(source_lms_engine, target_connection, "public", "mock_lms")
            _reset_sequences(target_connection, "public")
            _reset_sequences(target_connection, "mock_lms")
    finally:
        source_app_engine.dispose()
        source_lms_engine.dispose()
        target_engine.dispose()

    print(f"Copied application rows from {len(app_counts)} tables.")
    print(f"Copied LMS rows from {len(lms_counts)} tables.")
    print("Review the target Supabase database before switching the backend over.")


if __name__ == "__main__":
    main()
