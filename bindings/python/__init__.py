"""The installed Python projection of the native Agentic Workspace authority."""

from importlib.metadata import version

from .decision import DecisionContractError, answer_carried, invoke, invoke_carried, select_reference, start

__version__ = version("agentic-workspace")
__all__ = ["DecisionContractError", "answer_carried", "invoke", "invoke_carried", "select_reference", "start"]
