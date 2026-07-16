"""
Abstract Base Strategy Interface for MCQ Generators.
"""

from abc import ABC, abstractmethod


class MCQGenerator(ABC):
    """
    Contract that all Bloom level MCQ generator strategies must implement.
    """

    @abstractmethod
    def get_bloom_level(self) -> str:
        """
        Return the exact Bloom level name associated with this strategy.
        Values: Remember, Understand, Apply, Analyze, Evaluate, Create
        """
        pass
