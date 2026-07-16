"""
Prompt Validation Service.

Validates educational prompt inputs for completeness, size, and security.
Rejects prompts with missing required fields, prompt injection patterns,
oversized inputs, or malformed educational metadata.
"""

import re
from app.services.token_estimator import TokenEstimatorService

# Patterns indicative of prompt-injection attempts
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an)\s+\w+", re.IGNORECASE),
    re.compile(r"act\s+as\s+(?:a|an)\s+\w+", re.IGNORECASE),
    re.compile(r"pretend\s+(?:you\s+are|to\s+be)\s+", re.IGNORECASE),
    re.compile(r"<\s*script\s*>", re.IGNORECASE),
    re.compile(r"system\s*:\s*\[?\s*override", re.IGNORECASE),
    re.compile(r"\bDAN\b"),  # "Do Anything Now" jailbreak acronym
]

# Characters that are dangerous in prompt contexts (control chars, null bytes)
_DANGEROUS_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize(text: str) -> str:
    """
    Strip null bytes and dangerous control characters from a string.
    Preserves printable ASCII, Unicode letters, newlines (\\n), and tabs (\\t).
    """
    return _DANGEROUS_CHARS_RE.sub("", text)


def _check_injection(text: str, field_name: str) -> None:
    """
    Scan *text* for known prompt-injection patterns.

    :raises ValueError: If a suspicious pattern is found.
    """
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            raise ValueError(
                f"Security violation: Possible prompt injection detected in field '{field_name}'."
            )


class PromptValidationService:
    """
    Validates query prompt inputs and token sizing metrics before downstream LLM invocation.

    Responsibilities:
    - Presence checks (topic, context, Bloom levels, COs, constraints).
    - Size / token-budget enforcement.
    - Prompt-injection detection across all free-text inputs.
    - Unicode / control-character sanitization.
    """

    def __init__(self, token_estimator: TokenEstimatorService | None = None) -> None:
        self.token_estimator = token_estimator or TokenEstimatorService()

    def sanitize_and_check(self, text: str, field_name: str) -> str:
        """
        Sanitize control characters from *text* and verify it contains no
        injection patterns.  Returns the sanitized text.
        """
        sanitized = _sanitize(text)
        _check_injection(sanitized, field_name)
        return sanitized

    def validate_inputs(
        self,
        retrieved_context: str | None,
        topic: str | None,
        bloom_distribution: str | None,
        educational_constraints: str | None,
        faculty_preferences: str | None,
        course_outcomes: str | None = None,
    ) -> None:
        """
        Validate presence, correctness, and security of key prompt fields.

        :raises ValueError: On any validation failure.
        """
        # ── Presence checks ────────────────────────────────────────────────────
        if not retrieved_context or not retrieved_context.strip():
            raise ValueError("Validation failed: Missing retrieved context.")

        if not topic or not topic.strip():
            raise ValueError("Validation failed: Missing topic.")

        if not bloom_distribution or not bloom_distribution.strip():
            raise ValueError("Validation failed: Missing Bloom level distribution.")

        if not educational_constraints or not educational_constraints.strip():
            raise ValueError("Validation failed: Missing educational constraints.")

        if course_outcomes is not None and not course_outcomes.strip():
            raise ValueError("Validation failed: Missing course outcomes (COs).")

        # ── Bounds checks ──────────────────────────────────────────────────────
        if faculty_preferences and len(faculty_preferences) > 1000:
            raise ValueError(
                "Validation failed: Invalid faculty preferences (exceeds limit of 1000 characters)."
            )

        # ── Security checks ────────────────────────────────────────────────────
        fields_to_scan = {
            "topic": topic,
            "bloom_distribution": bloom_distribution,
            "educational_constraints": educational_constraints,
        }
        if course_outcomes:
            fields_to_scan["course_outcomes"] = course_outcomes
        if faculty_preferences:
            fields_to_scan["faculty_preferences"] = faculty_preferences

        for field_name, value in fields_to_scan.items():
            if value:
                _check_injection(value, field_name)

    def validate_size(self, full_prompt: str, max_tokens: int = 16000) -> int:
        """
        Estimate size and assert it does not exceed maximum token limit constraints.

        :raises ValueError: If the estimated token count exceeds *max_tokens*.
        :returns: Estimated token count.
        """
        tokens = self.token_estimator.estimate_tokens(full_prompt)
        if tokens > max_tokens:
            raise ValueError(
                f"Validation failed: Prompt too large (estimated {tokens} tokens, "
                f"max allowed: {max_tokens})."
            )
        return tokens
