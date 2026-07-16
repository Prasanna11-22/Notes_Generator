"""
Specialized Bloom Level MCQ Generator Strategies.
"""

from app.services.mcq.generator_base import MCQGenerator


class RememberGenerator(MCQGenerator):
    """Generates MCQs focusing on recall, definitions, facts, and basic concepts."""

    def get_bloom_level(self) -> str:
        return "Remember"


class UnderstandGenerator(MCQGenerator):
    """Generates MCQs focusing on explaining ideas, interpreting facts, and summarizing concepts."""

    def get_bloom_level(self) -> str:
        return "Understand"


class ApplyGenerator(MCQGenerator):
    """Generates MCQs focusing on applying information in new situations or solving problems."""

    def get_bloom_level(self) -> str:
        return "Apply"


class AnalyzeGenerator(MCQGenerator):
    """Generates MCQs focusing on drawing connections, comparing structures, or classifying components."""

    def get_bloom_level(self) -> str:
        return "Analyze"


class EvaluateGenerator(MCQGenerator):
    """Generates MCQs focusing on assessing proposals, justifying decisions, or evaluating metrics."""

    def get_bloom_level(self) -> str:
        return "Evaluate"


class CreateGenerator(MCQGenerator):
    """Generates MCQs focusing on synthesizing components, formulating hypotheses, or designing solutions."""

    def get_bloom_level(self) -> str:
        return "Create"
