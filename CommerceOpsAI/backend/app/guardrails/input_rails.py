"""NeMo Guardrails evaluation layer for incoming user requests.

Provides validation logic for user inputs, checking against predefined
Colang guardrail flows, and records evaluation audit events to the database.
"""

from dataclasses import dataclass
import os
import threading
from typing import Final, NamedTuple, Optional

from nemoguardrails import LLMRails, RailsConfig

from app.config import settings
from app.db import log_guardrail_event

_MAX_LOG_CONTENT_CHARS: Final[int] = 300


class _FlowSignature(NamedTuple):
  """Represents a marker pattern corresponding to a Colang flow definition."""

  marker: str
  flow_name: str
  allowed: bool


# Maps each Colang flow's fixed bot line (see rails.co) to a specific named flow.
# One entry per `define flow block ...` / `define flow flag ...` in the config,
# kept in definition order for straightforward verification against rails.co.
_FLOW_SIGNATURES: Final[tuple[_FlowSignature, ...]] = (
    _FlowSignature(
        marker="I'm scoped to order status",
        flow_name="off_topic",
        allowed=False,
    ),
    _FlowSignature(
        marker="can't set aside my operating instructions",
        flow_name="jailbreak_attempt",
        allowed=False,
    ),
    _FlowSignature(
        marker="Claimed authority or environment doesn't change",
        flow_name="authority_bypass_claim",
        allowed=False,
    ),
    _FlowSignature(
        marker="looks like an attempt to override",
        flow_name="prompt_injection_neutralized",
        allowed=True,
    ),
)

_RAILS_LOCK = threading.Lock()
_rails: Optional[LLMRails] = None


@dataclass(frozen=True)
class InputRailResult:
  """Outcome of an input guardrail evaluation.

  Attributes:
    allowed: Whether the input is permitted to proceed to downstream models.
    message: Output message text (sanitized message if blocked, or raw input).
    triggered_flow: Name of the Colang flow triggered, if any.
    blocked_reason: Deprecated backward-compatible alias for the blocked flow.
  """

  allowed: bool
  message: str
  triggered_flow: Optional[str] = None
  blocked_reason: Optional[str] = None


def _get_rails() -> LLMRails:
  """Initializes and returns the singleton LLMRails instance thread-safely."""
  global _rails
  if _rails is None:
    with _RAILS_LOCK:
      if _rails is None:
        os.environ["OPENAI_API_KEY"] = settings.OPENROUTER_API_KEY
        config = RailsConfig.from_path(settings.NEMO_CONFIG_DIR)
        _rails = LLMRails(config)
  return _rails


def check_input(
    text: str,
    session_id: Optional[str] = None,
) -> InputRailResult:
  """Runs the NeMo input guardrail checks on raw user input.

  Evaluates text against configured policies (off-topic, jailbreak attempts,
  authority-bypass claims, prompt injection). If an injection attempt is
  neutralized, the request is flagged but permitted.

  Args:
    text: The raw user prompt to evaluate.
    session_id: Optional identifier for logging and tracing user sessions.

  Returns:
    An InputRailResult containing validation status, the resulting message,
    and metadata on any triggered flow.
  """
  rails = _get_rails()
  response = rails.generate(messages=[{"role": "user", "content": text}])

  if isinstance(response, dict):
    content = str(response.get("content", ""))
  else:
    content = str(response)

  for sig in _FLOW_SIGNATURES:
    if sig.marker not in content:
      continue

    action = "flagged" if sig.allowed else "blocked"
    # rail_type carries the specific flow name to distinguish triggers in audit
    # tables and security monitoring dashboards.
    log_guardrail_event(
        session_id,
        f"input_rail:{sig.flow_name}",
        action,
        content[:_MAX_LOG_CONTENT_CHARS],
    )
    return InputRailResult(
        allowed=sig.allowed,
        message=content,
        triggered_flow=sig.flow_name,
        blocked_reason=None if sig.allowed else sig.flow_name,
    )

  return InputRailResult(allowed=True, message=text, triggered_flow=None)