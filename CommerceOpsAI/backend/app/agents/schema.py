"""Data schemas, domain models, and API contracts for the  system."""

import datetime
from typing import Literal, Optional, Self

from pydantic import BaseModel, Field


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
  """Clamps a floating point value to the interval [lo, hi].

  Args:
      value: The number to clamp.
      lo: The lower bound limit.
      hi: The upper bound limit.

  Returns:
      The clamped value within [lo, hi].
  """
  return max(lo, min(hi, value))


IntentLabel = Literal[
    "order_status",
    "refund_request",
    "billing_dispute",
    "policy_question",
    "merchandising_analytics",
    "market_intelligence",
    "off_topic",
]

RiskLevel = Literal["low", "medium", "high", "critical"]

JobStatus = Literal[
    "queued",
    "running",
    "awaiting_approval",
    "completed",
    "failed",
    "rejected",
]

EmployeeRole = Literal["manager", "tier1_support", "analyst"]


class IntentClassification(BaseModel):
  """Classification output for customer inquiries."""

  intent: IntentLabel
  confidence: float = Field(
      ge=0.0,
      le=1.0,
      description="0-1 confidence from the lightweight classifier.",
  )
  used_llm_fallback: bool = Field(
      default=False,
      description=(
          "True if confidence was too low and an LLM call was used instead."
      ),
  )


class OrderStatusResult(BaseModel):
  """Lookup result containing status and tracking information for an order."""

  order_id: str
  status: str
  carrier: Optional[str] = None
  estimated_delivery: Optional[str] = None
  summary: str


class RefundDecision(BaseModel):
  """Automated decision and anomaly evaluation for refund processing."""

  order_id: str
  amount_usd: float
  reason: str
  requires_human_approval: bool
  auto_flagged_anomaly: bool = Field(
      default=False,
      description=(
          "True if this looks like a just-under-threshold fraud pattern."
      ),
  )
  summary: str


class BillingDisputeResult(BaseModel):
  """Investigation details and initial resolution for billing disputes."""

  order_id: str
  dispute_summary: str
  resolution: str
  requires_human_approval: bool = False


class PolicyCitation(BaseModel):
  """Reference citation extracted from documentation."""

  source_document: str
  excerpt: str


class PolicyAnswer(BaseModel):
  """Synthesized answer to a customer policy question with citations."""

  answer: str
  citations: list[PolicyCitation] = Field(default_factory=list)
  used_graph_rag: bool = Field(
      default=False,
      description="Module 14: multi-hop graph traversal was used.",
  )


class AnalyticsQueryResult(BaseModel):
  """Natural language query execution result for operational analytics."""

  question: str
  sql_query: str
  result_summary: str
  row_count: int


class MarketIntelFinding(BaseModel):
  """Individual research finding or trend observation."""

  topic: str
  finding: str
  source: str


class MarketIntelReport(BaseModel):
  """Compiled market research and intelligence report."""

  query: str
  plan_steps: list[str]
  findings: list[MarketIntelFinding]
  executive_summary: str
  confidence: float = Field(
      description="0-100 self-assessed confidence, clamped in Python."
  )

  def clamped(self) -> Self:
    """Clamps the internal confidence score between 0.0 and 100.0."""
    self.confidence = _clamp(self.confidence)
    return self


# -----------------------------------------------------------------------------
# API Request / Response Models
# -----------------------------------------------------------------------------


class ChatRequest(BaseModel):
  """Inbound request payload from an employee console session."""

  message: str
  session_id: str = Field(
      description="Groups a multi-turn conversation for checkpointing."
  )
  employee_name: str = Field(
      description="The NorthPeak employee using the console for this request."
  )
  employee_role: EmployeeRole = Field(
      description=(
          "Determines whether this request requires manager sign-off before"
          " execution."
      )
  )
  customer_id: str = Field(
      description="Target customer account ID for this request."
  )
  order_id: str = Field(
      default="",
      description="Optional order ID if already referenced in context.",
  )


class ChatJobStatus(BaseModel):
  """Current execution status of an asynchronous chat background job."""

  session_id: str
  status: JobStatus
  current_node: Optional[str] = None
  progress_pct: int = 0
  error: Optional[str] = None
  employee_name: Optional[str] = None
  employee_role: Optional[EmployeeRole] = None
  customer_id: Optional[str] = None
  last_message: Optional[str] = None


class ApprovalDecision(BaseModel):
  """Recorded human reviewer intervention and decision."""

  session_id: str
  approved: bool
  reviewer: str
  comments: Optional[str] = None


class GuardrailEventOut(BaseModel):
  """Serialized guardrail audit trail event."""

  id: int
  session_id: Optional[str]
  rail_type: str
  action: str
  detail: str
  occurred_at: datetime.datetime


class ToneTestRequest(BaseModel):
  """Payload for running red-team tone evaluation checks."""

  text: str
  session_id: str = Field(default="redteam-tone-test")


class ToneTestResponse(BaseModel):
  """Output of a red-team tone safety evaluation."""

  original_text: str
  result_text: str
  flagged: bool