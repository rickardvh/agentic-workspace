"""The installed Python projection of the native Agentic Workspace authority."""

from importlib.metadata import version
from pkgutil import extend_path

# Source development joins the separately owned facade and provider portions.
# Wheels map both canonical source roots into the same installed package.
__path__ = extend_path(__path__, __name__)

from ._binding import DecisionContractError, answer_carried, invoke, invoke_carried, resources, select_reference, start

__version__ = version("agentic-workspace")
__all__ = ["DecisionContractError", "answer_carried", "invoke", "invoke_carried", "resources", "select_reference", "start"]
