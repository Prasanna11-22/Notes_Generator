"""
Assessment Blueprint Service for Assignments and Activities.
"""

from typing import Dict


class AssignmentBlueprintService:
    """
    Computes educational blueprint allocations for assignments.
    Divides maximum marks into specific task sections based on the targeted Bloom level.
    """

    @staticmethod
    def calculate_marks_distribution(total_marks: int, bloom_level: str) -> Dict[str, int]:
        """
        Distribute total marks across assessment tasks based on the targeted Bloom level.
        Uses integer division to prevent fractional mark issues.
        """
        if total_marks <= 0:
            return {}

        level = bloom_level.strip().capitalize()

        if level in ("Remember", "Understand"):
            # Conceptual focus
            recall_marks = int(total_marks * 0.6)
            explain_marks = total_marks - recall_marks
            return {
                "Conceptual Recall & Definition": recall_marks,
                "Explanation & Summarization": explain_marks,
            }
        elif level == "Apply":
            # Application/Problem solving focus
            theory_marks = int(total_marks * 0.3)
            apply_marks = total_marks - theory_marks
            return {
                "Theoretical Foundation": theory_marks,
                "Practical Application / Implementation": apply_marks,
            }
        elif level in ("Analyze", "Evaluate"):
            # Critique and comparison focus
            analysis_marks = int(total_marks * 0.4)
            critique_marks = total_marks - analysis_marks
            return {
                "Analytical Comparison & Dilation": analysis_marks,
                "Critical Evaluation & Justification": critique_marks,
            }
        elif level == "Create":
            # Design and synthesis focus
            design_marks = int(total_marks * 0.7)
            synthesis_marks = total_marks - design_marks
            return {
                "Design & Architecture Formulation": design_marks,
                "Synthesis & Solution Construction": synthesis_marks,
            }
        else:
            # Fallback uniform split
            part_a = int(total_marks * 0.5)
            part_b = total_marks - part_a
            return {
                "Part A: Theory & Concept": part_a,
                "Part B: Execution & Verification": part_b,
            }
