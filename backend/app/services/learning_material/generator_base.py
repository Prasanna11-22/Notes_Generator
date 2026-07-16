"""
Abstract Base Interface for Learning Material Generators.
"""

from abc import ABC, abstractmethod


class LearningMaterialGenerator(ABC):
    """
    Contract that all curriculum learning material generator strategies must implement.
    """

    @abstractmethod
    def get_generation_type(self) -> str:
        """
        Return the exact generation type string (e.g., 'Concept Explanation').
        Matches the database prompt templates.
        """
        pass

    @abstractmethod
    def get_prompt_template_name(self) -> str:
        """
        Return the lookup name for the default system prompt template.
        """
        pass
