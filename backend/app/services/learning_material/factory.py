"""
Generation Strategy Factory for resolving generator types.
"""

from typing import Dict, Type
from app.services.learning_material.generator_base import LearningMaterialGenerator
from app.services.learning_material.generators import (
    NotesGenerator,
    ConceptExplanationGenerator,
    WorkedExampleGenerator,
    SummaryGenerator,
    RevisionGenerator,
    DiscussionGenerator,
    ActivityGenerator,
    LearningObjectiveGenerator,
    KeyTakeawayGenerator,
    CommonMistakeGenerator,
    RealWorldApplicationGenerator,
)


class GenerationStrategyFactory:
    """
    Factory resolving generation type strings to specific generator strategies.
    
    Avoids large if-else statement blocks using a static lookup registry map.
    """

    _STRATEGY_MAP: Dict[str, Type[LearningMaterialGenerator]] = {
        "Topic Notes": NotesGenerator,
        "Concept Explanation": ConceptExplanationGenerator,
        "Worked Examples": WorkedExampleGenerator,
        "Summary Notes": SummaryGenerator,
        "Revision Notes": RevisionGenerator,
        "Discussion Questions": DiscussionGenerator,
        "Classroom Activities": ActivityGenerator,
        "Learning Objectives": LearningObjectiveGenerator,
        "Key Takeaways": KeyTakeawayGenerator,
        "Common Mistakes": CommonMistakeGenerator,
        "Real-world Applications": RealWorldApplicationGenerator,
    }

    @classmethod
    def get_generator(cls, generator_type: str) -> LearningMaterialGenerator:
        """
        Resolve generator type string to concrete generator class instance.
        """
        strategy_class = cls._STRATEGY_MAP.get(generator_type)
        if not strategy_class:
            valid_types = ", ".join(cls._STRATEGY_MAP.keys())
            raise ValueError(
                f"Unsupported generation type: '{generator_type}'. "
                f"Must be one of: {valid_types}."
            )
        return strategy_class()
