"""
Concrete implementations of Learning Material Generator strategies.
"""

from app.services.learning_material.generator_base import LearningMaterialGenerator


class NotesGenerator(LearningMaterialGenerator):
    def get_generation_type(self) -> str:
        return "Learning Material"

    def get_prompt_template_name(self) -> str:
        return "System Default: Learning Material"


class ConceptExplanationGenerator(LearningMaterialGenerator):
    def get_generation_type(self) -> str:
        return "Concept Explanation"

    def get_prompt_template_name(self) -> str:
        return "System Default: Concept Explanation"


class WorkedExampleGenerator(LearningMaterialGenerator):
    def get_generation_type(self) -> str:
        return "Worked Examples"

    def get_prompt_template_name(self) -> str:
        return "System Default: Worked Examples"


class SummaryGenerator(LearningMaterialGenerator):
    def get_generation_type(self) -> str:
        return "Summary Notes"

    def get_prompt_template_name(self) -> str:
        return "System Default: Summaries"


class RevisionGenerator(LearningMaterialGenerator):
    def get_generation_type(self) -> str:
        return "Revision Notes"

    def get_prompt_template_name(self) -> str:
        return "System Default: Revision Notes"


class DiscussionGenerator(LearningMaterialGenerator):
    def get_generation_type(self) -> str:
        return "Discussion Questions"

    def get_prompt_template_name(self) -> str:
        return "System Default: Discussion Questions"


class ActivityGenerator(LearningMaterialGenerator):
    def get_generation_type(self) -> str:
        return "Classroom Activities"

    def get_prompt_template_name(self) -> str:
        return "System Default: Activities"


class LearningObjectiveGenerator(LearningMaterialGenerator):
    def get_generation_type(self) -> str:
        return "Learning Objectives"

    def get_prompt_template_name(self) -> str:
        return "System Default: Learning Objectives"


class KeyTakeawayGenerator(LearningMaterialGenerator):
    def get_generation_type(self) -> str:
        return "Key Takeaways"

    def get_prompt_template_name(self) -> str:
        return "System Default: Key Takeaways"


class CommonMistakeGenerator(LearningMaterialGenerator):
    def get_generation_type(self) -> str:
        return "Common Mistakes"

    def get_prompt_template_name(self) -> str:
        return "System Default: Common Mistakes"


class RealWorldApplicationGenerator(LearningMaterialGenerator):
    def get_generation_type(self) -> str:
        return "Real-world Applications"

    def get_prompt_template_name(self) -> str:
        return "System Default: Real-world Applications"
