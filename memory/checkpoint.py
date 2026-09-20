from __future__ import annotations

import os
from dotenv import load_dotenv
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

load_dotenv()

_CHECKPOINT_POOL: ConnectionPool | None = None


def _postgres_conninfo() -> str:
    """Build the checkpoint database connection string from environment settings."""
    return make_conninfo(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "sentinelops"),
        user=os.getenv("POSTGRES_USER", "sentinelops"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )


def create_checkpointer() -> BaseCheckpointSaver:
    """Create the configured LangGraph checkpoint backend.

    PostgreSQL is the default because SentinelOps needs durable investigation
    state for human-in-the-loop workflows. Set SENTINELOPS_CHECKPOINT_BACKEND=memory
    for isolated tests or lightweight local experiments.
    """
    backend = os.getenv("SENTINELOPS_CHECKPOINT_BACKEND", "postgres").lower()

    if backend == "memory":
        return MemorySaver()

    if backend != "postgres":
        raise ValueError(
            "SENTINELOPS_CHECKPOINT_BACKEND must be 'postgres' or 'memory'"
        )

    global _CHECKPOINT_POOL
    if _CHECKPOINT_POOL is None:
        _CHECKPOINT_POOL = ConnectionPool(
            conninfo=_postgres_conninfo(),
            min_size=1,
            max_size=int(os.getenv("SENTINELOPS_CHECKPOINT_POOL_MAX_SIZE", "5")),
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
            open=False,
        )
        _CHECKPOINT_POOL.open()
        _CHECKPOINT_POOL.wait()

    checkpointer = PostgresSaver(_CHECKPOINT_POOL)
    checkpointer.setup()
    return checkpointer


def close_checkpointer() -> None:
    """Close the shared PostgreSQL checkpoint connection pool."""
    global _CHECKPOINT_POOL
    if _CHECKPOINT_POOL is not None:
        _CHECKPOINT_POOL.close()
        _CHECKPOINT_POOL = None


atexit.register(close_checkpointer)
