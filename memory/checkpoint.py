from langgraph.checkpoint.memory import MemorySaver


def create_checkpointer() -> MemorySaver:
    """Create an in-process checkpointer for short-term incident memory."""
    return MemorySaver()
