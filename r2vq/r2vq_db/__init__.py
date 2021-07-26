from pathlib import Path
from peewee import SqliteDatabase

db = SqliteDatabase(
    Path(__file__).parent.joinpath("db_files/recipe.db"),
    pragmas={
        "journal_mode": "wal",
        "cache_size": -1 * 64000,  # 64MB
        "foreign_keys": 1,
        "ignore_check_constraints": 0,
        "synchronous": 0,
    },
)
