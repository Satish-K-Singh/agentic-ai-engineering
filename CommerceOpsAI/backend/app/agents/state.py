"""Defines state representations for agent workflows."""

from typing import Any, Optional, TypedDict


class SupervisorState(TypedDict, total=False):
  """Represents the state of a supervisor agent across workflow execution.

  Attributes:
    session_id: Unique identifier for the current session.
    raw_message: Unprocessed user input message.
    employee_name: Name of the employee handling or referenced in the session.
    employee_role: Organizational role or title of the employee.
    customer_id: Unique customer identifier.
    order_id: Unique identifier for the customer order.
    guard_allowed: Whether the safety guardrail approved the input.
    guard_notes: Audit logs or flags recorded by the guardrail.
    redacted_message: Message content after scrubbing PII or sensitive data.
    pii_entities_found: Total count of PII entities detected.
    cost_data_flagged: Indicates whether restricted financial data was detected.
    intent: Classified intent of the message.
    intent_confidence: Model confidence score for the detected intent (0.0 to 1.0).
    used_llm_feedback: Whether LLM self-reflection or feedback loops were invoked.
    order_status_result: Payload returned by the order status lookup tool.
    refund_result: Payload returned by the refund management tool.
    billing_result: Payload returned by the billing inspection tool.
    policy_answer: Payload or response retrieved from policy documentation.
    analytics_result: Payload generated from business analytics queries.
    market_intel_result: Payload generated from market intelligence sources.
    final_response_text: Final generated response ready for delivery.
    requires_human_approval: Whether the workflow requires human-in-the-loop review.
    approved: Human reviewer decision; None if pending review.
    reviewer: Identifier or LDAP of the human reviewer.
    approval_comments: Feedback or rationale provided by the reviewer.
    current_node: Current node or stage name in the execution graph.
    progress_pct: Overall workflow completion percentage (0-100).
    error: Error message if the workflow encountered a failure; None otherwise.
  """

  session_id: str
  raw_message: str
  employee_name: str
  employee_role: str
  customer_id: str
  order_id: str

  guard_allowed: bool
  guard_notes: list[str]

  redacted_message: str
  pii_entities_found: int
  cost_data_flagged: bool

  intent: str
  intent_confidence: float
  used_llm_feedback: bool

  order_status_result: Optional[dict[str, Any]]
  refund_result: Optional[dict[str, Any]]
  billing_result: Optional[dict[str, Any]]
  policy_answer: Optional[dict[str, Any]]
  analytics_result: Optional[dict[str, Any]]
  market_intel_result: Optional[dict[str, Any]]

  final_response_text: str

  requires_human_approval: bool
  approved: Optional[bool]
  reviewer: Optional[str]
  approval_comments: Optional[str]

  current_node: str
  progress_pct: int
  error: Optional[str]