"""
Rubric Preparation Service for Assignments and Activities.
"""

from typing import Any, Dict, List


class RubricPreparationService:
    """
    Handles compilation, parsing, verification, and formatting of structured grading rubrics.
    """

    REQUIRED_KEYS = {
        "assessment_criteria",
        "expected_learning_outcomes",
        "evaluation_guidelines",
        "mark_distribution",
        "suggested_solution_outline",
    }

    @classmethod
    def validate_rubric_structure(cls, rubric: Dict[str, Any]) -> None:
        """
        Ensure all required components exist in the rubric dictionary.
        """
        if not rubric:
            raise ValueError("Rubric data is empty.")

        # Normalize keys for robustness
        normalized = {k.lower().replace("_", ""): k for k in rubric.keys()}

        missing = []
        for req_key in cls.REQUIRED_KEYS:
            normalized_req = req_key.replace("_", "")
            if normalized_req not in normalized:
                missing.append(req_key)

        if missing:
            missing_str = ", ".join(missing)
            raise ValueError(f"Rubric is missing required sections: {missing_str}")

    @classmethod
    def format_rubric_to_markdown(cls, rubric: Dict[str, Any]) -> str:
        """
        Convert structured rubric dictionary to readable markdown representation.
        """
        cls.validate_rubric_structure(rubric)

        lines = ["# Grading Rubric & Evaluation Guide\n"]

        # Assessment Criteria
        lines.append("## Assessment Criteria")
        criteria = rubric.get("assessment_criteria") or rubric.get("assessmentcriteria")
        if isinstance(criteria, list):
            for c in criteria:
                lines.append(f"- {c}")
        else:
            lines.append(str(criteria))
        lines.append("")

        # Expected Learning Outcomes
        lines.append("## Expected Learning Outcomes")
        outcomes = rubric.get("expected_learning_outcomes") or rubric.get("expectedlearningoutcomes")
        if isinstance(outcomes, list):
            for o in outcomes:
                lines.append(f"- {o}")
        else:
            lines.append(str(outcomes))
        lines.append("")

        # Evaluation Guidelines
        lines.append("## Evaluation Guidelines")
        guidelines = rubric.get("evaluation_guidelines") or rubric.get("evaluationguidelines")
        if isinstance(guidelines, list):
            for g in guidelines:
                lines.append(f"- {g}")
        else:
            lines.append(str(guidelines))
        lines.append("")

        # Mark Distribution
        lines.append("## Mark Distribution")
        dist = rubric.get("mark_distribution") or rubric.get("markdistribution")
        if isinstance(dist, dict):
            for k, v in dist.items():
                lines.append(f"- **{k}**: {v}")
        elif isinstance(dist, list):
            for item in dist:
                lines.append(f"- {item}")
        else:
            lines.append(str(dist))
        lines.append("")

        # Suggested Solution Outline
        lines.append("## Suggested Solution Outline")
        sol = rubric.get("suggested_solution_outline") or rubric.get("suggestestedsolutionoutline") or rubric.get("suggested_solution")
        if isinstance(sol, list):
            for step in sol:
                lines.append(f"1. {step}")
        else:
            lines.append(str(sol))
        lines.append("")

        return "\n".join(lines)
