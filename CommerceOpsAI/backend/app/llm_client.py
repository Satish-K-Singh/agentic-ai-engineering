#This VS code is having copilot. 
"""LLM factory functions configured for role-specific tasks."""

from crewai import LLM as CrewAILLM
from langchain_openai import ChatOpenAI

from app.config import settings


def get_llm(
    temperature: float = 0.0,
    max_tokens: int = 1000,
) -> ChatOpenAI:
  """Returns a ChatOpenAI instance configured with application settings.

  Args:
    temperature: Sampling temperature between 0.0 and 2.0. Higher values make
      the output more random, while lower values make it more deterministic.
    max_tokens: The maximum number of tokens to generate in the chat completion.

  Returns:
    An initialized ChatOpenAI client instance.

  Raises:
    ValueError: If OPENAI_API_KEY is not set in application settings.
  """
  if not settings.OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in the environment variables.")

  return ChatOpenAI(
      model=settings.MODEL,
      api_key=settings.OPENAI_API_KEY,
      base_url=settings.BASE_URL,
      temperature=temperature,
      max_tokens=max_tokens,
  )


def router_llm() -> ChatOpenAI:
  """Returns a ChatOpenAI instance for intent routing."""
  return get_llm(temperature=0.0, max_tokens=settings.MAX_TOKENS_ROUTER)


def supervisor_llm() -> ChatOpenAI:
  """Returns a ChatOpenAI instance for the supervisor agent."""
  return get_llm(temperature=0.0, max_tokens=settings.MAX_TOKENS_SUPERVISOR)


def agent_llm() -> ChatOpenAI:
  """Returns a ChatOpenAI instance for task execution agents."""
  return get_llm(temperature=0.1, max_tokens=settings.MAX_TOKENS_AGENT)


def crew_agent_llm() -> CrewAILLM:
  """Returns a CrewAILLM instance configured for multi-agent crew execution.

  Returns:
    An initialized CrewAILLM client instance routed through OpenRouter.

  Raises:
    RuntimeError: If OPENROUTER_API_KEY is not set in application settings.
  """
  if not getattr(settings, "OPENROUTER_API_KEY", None):
    raise RuntimeError(
        "OPENROUTER_API_KEY is not set. Copy .env.example to .env and add"
        " your OpenRouter key before running any live-model demo."
    )
  return CrewAILLM(
      model=f"openrouter/{settings.MODEL}",
      api_key=settings.OPENROUTER_API_KEY,
      max_tokens=settings.MAX_TOKENS_CREW_AGENT,
      temperature=0.2,
  )


def deep_agent_llm() -> ChatOpenAI:
  """Returns a ChatOpenAI instance for complex, long-context reasoning."""
  return get_llm(temperature=0.2, max_tokens=settings.MAX_TOKENS_DEEP_AGENT)


def summary_llm() -> ChatOpenAI:
  """Returns a ChatOpenAI instance for deterministic summarization."""
  return get_llm(temperature=0.0, max_tokens=settings.MAX_TOKENS_SUMMARY)