"""
Strategy Factory for resolving MCQ Bloom generators.
"""

from typing import Dict, Type
from app.services.mcq.generator_base import MCQGenerator
from app.services.mcq.generators import (
    RememberGenerator,
    UnderstandGenerator,
    ApplyGenerator,
    AnalyzeGenerator,
    EvaluateGenerator,
    CreateGenerator,
)


class GenerationStrategyFactory:
    """
    Registry factory returning Bloom level MCQ strategy class instances.
    """

    _STRATEGY_MAP: Dict[str, Type[MCQGenerator]] = {
        "Remember": RememberGenerator,
        "Understand": UnderstandGenerator,
        "Apply": ApplyGenerator,
        "Analyze": AnalyzeGenerator,
        "Evaluate": EvaluateGenerator,
        "Create": CreateGenerator,
    }

    @classmethod
    def get_generator(cls, bloom_level: str) -> MCQGenerator:
        """
        Resolve Bloom level string to concrete strategy instance.
        """
        normalized_level = bloom_level.strip().capitalize()
        strategy_class = cls._STRATEGY_MAP.get(normalized_level)
        if not strategy_class:
            valid_levels = ", ".join(cls._STRATEGY_MAP.keys())
            raise ValueError(
                f"Unsupported Bloom level: '{bloom_level}'. "
                f"Must be one of: {valid_levels}."
            )
        return strategy_class()
