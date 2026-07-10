"""
Per-session conversation memory.

This is an in-process dict for simplicity — swap `_STORE` for a Redis-backed
implementation (same interface) to run multiple API instances behind a load balancer.
"""

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage
from langchain_community.chat_message_histories import ChatMessageHistory

_STORE: dict[str, BaseChatMessageHistory] = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in _STORE:
        _STORE[session_id] = ChatMessageHistory()
    return _STORE[session_id]


def clear_session(session_id: str) -> None:
    _STORE.pop(session_id, None)


def get_history_messages(session_id: str) -> list[BaseMessage]:
    return get_session_history(session_id).messages
