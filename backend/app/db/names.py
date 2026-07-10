from app.config import settings


def table_name(name: str) -> str:
    return f"{settings.db_table_prefix}{name}"


def fk_column(table: str, column: str = "id") -> str:
    return f"{table_name(table)}.{column}"


def index_name(table: str, suffix: str) -> str:
    return f"ix__{table_name(table)}__{suffix}"


def unique_index_name(table: str, suffix: str) -> str:
    return f"uq__{table_name(table)}__{suffix}"
