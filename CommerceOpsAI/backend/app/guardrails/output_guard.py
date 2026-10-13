import json
from typing import Type, TypeVar

from guardrails import Guard
from guardrails.validator_base import FailResult, PassResult, Validator, register_validator
from langchian_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.db import log_guardrail_event
from app.guardrails.pii_redaction import scrub_cost_data_from_output
from app.llm_client import router_llm

T = TypeVar("T", bound=BaseModel)

_schema_guards: dict[type, Guard] = {}
_tone_guard: Guard | None = None

@register_validator(name="commerceops/professional-tone", data_type="string")
class ProfessionalToneCheck(Validator):
    def validate(self, value, metadata):
        
