"""
Duplicate Detector Service for multiple choice questions.
"""

from typing import List


class MCQDuplicateDetector:
    """
    Computes wording overlap and similarity scoring to detect duplicate questions.
    """

    @classmethod
    def check_duplicate(cls, new_question_text: str, existing_questions: List[str], threshold: float = 0.6) -> None:
        """
        Compare newly generated question stem against a list of existing stems.
        
        Raises ValueError if Jaccard similarity exceeds the threshold.
        """
        new_words = set(cls._tokenize(new_question_text))
        if not new_words:
            return

        for idx, existing in enumerate(existing_questions):
            existing_words = set(cls._tokenize(existing))
            if not existing_words:
                continue

            intersection = new_words.intersection(existing_words)
            union = new_words.union(existing_words)
            similarity = len(intersection) / len(union)

            if similarity > threshold:
                raise ValueError(
                    f"Duplicate detection failed: New question is too similar to "
                    f"an existing question (similarity: {similarity:.2f})."
                )

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenize text into lowercased alphanumeric words, stripping punctuation."""
        import re
        return [w.lower() for w in re.findall(r"\w+", text) if len(w) > 2]
