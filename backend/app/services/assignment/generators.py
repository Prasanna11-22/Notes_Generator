"""
Specialized Assignment and Activity Generator Strategies.
"""

from app.services.assignment.generator_base import AssignmentGenerator


class DescriptiveGenerator(AssignmentGenerator):
    """Generates descriptive assignment questions and prompts."""

    def get_generator_type(self) -> str:
        return "Descriptive Questions"


class ProgrammingGenerator(AssignmentGenerator):
    """Generates coding tasks, programming specifications, and unit testing guidelines."""

    def get_generator_type(self) -> str:
        return "Programming Assignments"


class CaseStudyGenerator(AssignmentGenerator):
    """Generates educational case studies and context scenario questions."""

    def get_generator_type(self) -> str:
        return "Case Studies"


class ProblemSolvingGenerator(AssignmentGenerator):
    """Generates step-by-step problem solving numerical/analytical questions."""

    def get_generator_type(self) -> str:
        return "Problem Solving Questions"


class AnalyticalGenerator(AssignmentGenerator):
    """Generates critical thinking and analytical evaluation prompts."""

    def get_generator_type(self) -> str:
        return "Analytical Questions"


class DesignGenerator(AssignmentGenerator):
    """Generates design-based (architectural, database, engineering) design prompts."""

    def get_generator_type(self) -> str:
        return "Design-Based Questions"


class MiniProjectGenerator(AssignmentGenerator):
    """Generates practical mini project topics and setup guides."""

    def get_generator_type(self) -> str:
        return "Mini Projects"


class ActivityGenerator(AssignmentGenerator):
    """
    Generates classroom and learning activities (Group, Individual, Think-Pair-Share, 
    Collaborative, Inquiry-Based).
    """

    def get_generator_type(self) -> str:
        return "Learning Activities"
