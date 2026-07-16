"""
Validation Service for checking Learning Material quality and alignment.
"""

import re


class LearningMaterialValidator:
    """
    Validates generated materials against content structure, quality, 
    curriculum alignment, and Bloom's taxonomy constraints.
    """

    # Typical active verbs for Bloom's Taxonomy Cognitive Levels
    BLOOM_VERBS = {
        "remember": ["define", "recall", "list", "name", "state", "identify", "memorize", "repeat"],
        "understand": ["explain", "describe", "summarize", "discuss", "classify", "locate", "translate"],
        "apply": ["apply", "solve", "implement", "calculate", "use", "demonstrate", "illustrate", "run"],
        "analyze": ["analyze", "compare", "contrast", "differentiate", "distinguish", "examine", "model"],
        "evaluate": ["evaluate", "judge", "assess", "critique", "defend", "justify", "rate", "verify"],
        "create": ["create", "design", "construct", "develop", "generate", "write", "formulate", "build"],
    }

    @classmethod
    def validate_content(cls, text: str) -> None:
        """
        Validate basic structural layout and filter out common hallucination/placeholder artifacts.
        """
        if not text or not text.strip():
            raise ValueError("Generated material content is empty.")

        # Check for unreplaced placeholders or templates
        placeholders = [
            r"\[Insert\s+.*?\]",
            r"\[Your\s+Name\]",
            r"<insert\s+.*?>",
            r"TODO:",
            r"Insert\s+topic\s+here"
        ]
        for pattern in placeholders:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValueError(f"Content validation failed: Found placeholder match for '{pattern}'.")

        # Check for duplicate paragraphs (simple exact string match)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        unique_paragraphs = set()
        for p in paragraphs:
            # We ignore very short paragraphs (like markdown headers or lists) to avoid false positives
            if len(p) > 100:
                # Clean whitespace for comparison
                cleaned_p = " ".join(p.split()).lower()
                if cleaned_p in unique_paragraphs:
                    raise ValueError("Content validation failed: Duplicate paragraph detected in output.")
                unique_paragraphs.add(cleaned_p)

        # Check for basic readable structure (e.g. at least one header or list)
        has_headers = re.search(r"^#+\s+", text, re.MULTILINE)
        has_lists = re.search(r"^\s*[-*+]\s+", text, re.MULTILINE) or re.search(r"^\s*\d+\.\s+", text, re.MULTILINE)
        if not (has_headers or has_lists):
            raise ValueError("Content validation failed: Material lacks clean formatting structure (no headers or lists).")

    @classmethod
    def validate_educational_alignment(
        cls,
        text: str,
        topic: str,
        bloom_level: str | None = None,
        course_outcomes: list[str] | None = None,
    ) -> None:
        """
        Validate educational alignment mapping.
        - Asserves target topic terms exist in the content.
        - Checks verb footprint matches the Bloom taxonomy level (if provided).
        - Verifies keyword association with course outcomes (if provided).
        """
        # 1. Topic coverage check
        topic_words = [w.lower() for w in re.findall(r"\w+", topic) if len(w) > 3]
        text_lower = text.lower()
        
        # At least one major word of the topic name should exist in the generated text
        if topic_words:
            matched_words = [w for w in topic_words if w in text_lower]
            if not matched_words:
                raise ValueError(f"Educational validation failed: Content does not cover the requested topic '{topic}'.")

        # 2. Bloom Level check
        if bloom_level:
            level_key = bloom_level.lower().strip()
            # If it's a valid bloom level name, check matching active verb density
            if level_key in cls.BLOOM_VERBS:
                target_verbs = cls.BLOOM_VERBS[level_key]
                # Check if at least one target verb or its common variants (e.g. -ed, -ing, -s) is in the text
                has_verb = False
                for verb in target_verbs:
                    # Match word boundary or common forms
                    pattern = rf"\b{verb}\w*\b"
                    if re.search(pattern, text_lower):
                        has_verb = True
                        break
                if not has_verb:
                    # Instead of raising immediately (to prevent brittle failures on creative text), 
                    # we log a warning or raise a validation exception if strict checking is configured.
                    # We will raise a ValueError if it completely fails to use any verb associated 
                    # with understanding or creating, or if it is a rigid verification test.
                    # Let's raise a ValueError to enforce Bloom level alignment in unit tests.
                    raise ValueError(f"Educational validation failed: Verbs do not align with Bloom level '{bloom_level}'.")

        # 3. Course Outcomes check
        if course_outcomes:
            # Check for keyword overlap between the outcomes text and generated text
            for outcome in course_outcomes:
                outcome_words = [w.lower() for w in re.findall(r"\w+", outcome) if len(w) > 4]
                if outcome_words:
                    # Ensure at least 1-2 keywords of the course outcomes overlap in the text
                    overlap = [w for w in outcome_words if w in text_lower]
                    if not overlap:
                        # Allow slight tolerance but require at least some alignment
                        raise ValueError(f"Educational validation failed: Content is not aligned with Course Outcome: '{outcome}'.")
