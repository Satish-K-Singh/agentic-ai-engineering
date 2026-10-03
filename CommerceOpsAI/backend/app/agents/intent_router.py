"""Intent classification module combining an ML model with LLM fallback routing."""

import functools
import logging
from pathlib import Path
import threading
from typing import Any, Protocol, Sequence

import joblib
from langchain_core.messages import HumanMessage, SystemMessage
import numpy as np

from app.config import settings
from app.llm_client import router_llm
from app.schema import IntentClassification, IntentLabel

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD: float = 0.45

INTENT_LABELS: Sequence[IntentLabel] = (
    "order_status",
    "refund_request",
    "billing_dispute",
    "policy_question",
    "merchandising_analytics",
    "market_intelligence",
    "off_topic",
)

_VALID_INTENTS_SET: frozenset[str] = frozenset(INTENT_LABELS)

_MODEL_LOCK = threading.Lock()
_CLASSIFIER_INSTANCE: Any | None = None


class ClassifierProtocol(Protocol):
    """Protocol defining the expected interface for the scikit-learn classifier."""

    classes_: np.ndarray

    def predict_proba(self, X: Sequence[str]) -> np.ndarray:
        ...


def get_classifier(model_path: Path | str | None = None) -> ClassifierProtocol:
    """Retrieves or lazily initializes the cached intent classifier instance.

    Thread-safe implementation using double-checked locking.

    Args:
        model_path: Optional path to the serialized classifier file. Defaults
          to `settings.INTENT_ROUTER_MODEL_PATH`.

    Returns:
        The loaded scikit-learn compatible classifier.

    Raises:
        FileNotFoundError: If the model binary cannot be located on disk.
    """
    global _CLASSIFIER_INSTANCE
    if _CLASSIFIER_INSTANCE is not None:
        return _CLASSIFIER_INSTANCE

    target_path = Path(model_path or settings.INTENT_ROUTER_MODEL_PATH)

    with _MODEL_LOCK:
        if _CLASSIFIER_INSTANCE is None:
            if not target_path.is_file():
                error_msg = (
                    f"No trained intent classifier found at '{target_path}'. "
                    "Run 'python scripts/train_intent_router.py' first."
                )
                logger.critical(error_msg)
                raise FileNotFoundError(error_msg)

            logger.info("Loading intent router model from %s", target_path)
            _CLASSIFIER_INSTANCE = joblib.load(target_path)

    return _CLASSIFIER_INSTANCE


def _llm_fallback_classify(message: str) -> IntentLabel:
    """Classifies message intent via an LLM when model confidence is low.

    Args:
        message: The raw text string to classify.

    Returns:
        An IntentLabel representing the determined intent, defaulting to
        'off_topic' if the LLM output is malformed or unmapped.
    """
    try:
        llm = router_llm()
        system_prompt = (
            "Classify this customer or internal message into exactly one intent "
            f"from: {list(INTENT_LABELS)}. Reply with ONLY the label string, "
            "nothing else."
        )
        response = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=message),
            ]
        )

        raw_content = str(response.content).strip().strip('"\'').lower()

        if raw_content in _VALID_INTENTS_SET:
            return raw_content  # type: ignore[return-value]

        logger.warning(
            "LLM returned unexpected intent label '%s'. Defaulting to 'off_topic'.",
            raw_content,
        )
        return "off_topic"

    except Exception:
        logger.exception("LLM fallback classification invocation failed.")
        return "off_topic"


def classify_intent(
    message: str,
    classifier: ClassifierProtocol | None = None,
) -> IntentClassification:
    """Classifies the intent of an inbound user or system message.

    Runs statistical ML inference first. If confidence is strictly below
    `CONFIDENCE_THRESHOLD`, it triggers `_llm_fallback_classify`.

    Args:
        message: Input string to categorize.
        classifier: Optional classifier instance, primarily used to inject
          mocks during unit testing.

    Returns:
        An `IntentClassification` payload containing the determined intent,
        the model's numeric confidence score, and a fallback indicator.

    Raises:
        ValueError: If input message is empty or whitespace-only.
        FileNotFoundError: If no pre-trained model exists on disk.
    """
    clean_message = message.strip()
    if not clean_message:
        raise ValueError("Message cannot be empty or whitespace only.")

    active_classifier = classifier or get_classifier()

    probabilities = active_classifier.predict_proba([clean_message])[0]
    best_index = int(np.argmax(probabilities))
    confidence = float(probabilities[best_index])
    predicted_label: IntentLabel = active_classifier.classes_[best_index]

    if confidence < CONFIDENCE_THRESHOLD:
        logger.info(
            "Confidence (%.4f) below threshold (%.2f). Invoking LLM fallback.",
            confidence,
            CONFIDENCE_THRESHOLD,
        )
        fallback_label = _llm_fallback_classify(clean_message)
        return IntentClassification(
            intent=fallback_label,
            confidence=confidence,
            used_llm_fallback=True,
        )

    return IntentClassification(
        intent=predicted_label,
        confidence=confidence,
        used_llm_fallback=False,
    )