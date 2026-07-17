"""
Strategy Factory for resolving Assignment and Activity generators.
"""

from typing import Dict, Type
from app.services.assignment.generator_base import AssignmentGenerator
from app.services.assignment.generators import (
    DescriptiveGenerator,
    ProgrammingGenerator,
    CaseStudyGenerator,
    ProblemSolvingGenerator,
    AnalyticalGenerator,
    DesignGenerator,
    MiniProjectGenerator,
    ActivityGenerator,
)


class GenerationStrategyFactory:
    """
    Registry factory returning specialized assignment and learning activity generator strategies.
    """

    _STRATEGY_MAP: Dict[str, Type[AssignmentGenerator]] = {
        "Descriptive Questions": DescriptiveGenerator,
        "Programming Assignments": ProgrammingGenerator,
        "Case Studies": CaseStudyGenerator,
        "Problem Solving Questions": ProblemSolvingGenerator,
        "Analytical Questions": AnalyticalGenerator,
        "Design-Based Questions": DesignGenerator,
        "Mini Projects": MiniProjectGenerator,
        "Group Activities": ActivityGenerator,
        "Individual Activities": ActivityGenerator,
        "Think-Pair-Share Activities": ActivityGenerator,
        "Collaborative Learning Activities": ActivityGenerator,
        "Inquiry-Based Activities": ActivityGenerator,
        "Learning Activities": ActivityGenerator,
    }

    @classmethod
    def get_generator(cls, generator_type: str) -> AssignmentGenerator:
        """
        Resolve generator type string to concrete strategy instance.
        """
        # Clean and case insensitive check
        cleaned_type = generator_type.strip()
        
        # Try exact match first
        strategy_class = cls._STRATEGY_MAP.get(cleaned_type)
        if not strategy_class:
            # Try case insensitive search
            for key, val in cls._STRATEGY_MAP.items():
                if key.lower() == cleaned_type.lower():
                    strategy_class = val
                    break
        
        if not strategy_class:
            valid_types = ", ".join(cls._STRATEGY_MAP.keys())
            raise ValueError(
                f"Unsupported generator type: '{generator_type}'. "
                f"Must be one of: {valid_types}."
            )
        return strategy_class()
