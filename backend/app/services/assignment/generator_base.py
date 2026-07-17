"""
Abstract Base Strategy Interface for Assignment and Learning Activity Generators.
"""

from abc import ABC, abstractmethod


class AssignmentGenerator(ABC):
    """
    Contract that all assignment and activity generator strategies must implement.
    """

    @abstractmethod
    def get_generator_type(self) -> str:
        """
        Return the exact generator type name associated with this strategy.
        """
        pass
