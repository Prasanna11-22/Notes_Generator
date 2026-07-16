"""
Assessment Blueprint Service for calculating exact question distributions.
"""

from typing import Dict


class AssessmentBlueprintService:
    """
    Computes exact question allocations for each cognitive level and difficulty 
    tier using the Largest Remainder Method, avoiding float approximation errors.
    """

    @staticmethod
    def calculate_distribution(total_questions: int, distribution: Dict[str, float]) -> Dict[str, int]:
        """
        Distribute a total number of questions exactly matching float percentages.
        
        Uses the Largest Remainder Method (Hare-Niemeyer) to round float values
        such that the sum of output integers exactly equals total_questions.
        """
        if total_questions <= 0:
            return {}

        # 1. Clean and filter positive percentages
        cleaned = {k: max(0.0, float(v)) for k, v in distribution.items() if v > 0.0}
        if not cleaned:
            # Fallback if no valid categories are mapped
            return {"Understand": total_questions}

        # 2. Normalize distribution so it sums to 1.0 (100%)
        total_pct = sum(cleaned.values())
        normalized = {k: v / total_pct for k, v in cleaned.items()}

        # 3. Calculate float targets and base integer parts
        float_counts = {k: total_questions * pct for k, pct in normalized.items()}
        int_counts = {k: int(val) for k, val in float_counts.items()}

        # 4. Compute remainder fractions
        remainders = {k: float_counts[k] - int_counts[k] for k in normalized}

        # 5. Distribute remaining questions based on largest fractional remainders
        allocated = sum(int_counts.values())
        difference = total_questions - allocated

        if difference > 0:
            # Sort categories by remainder value descending
            sorted_keys = sorted(remainders.keys(), key=lambda k: remainders[k], reverse=True)
            for i in range(difference):
                key = sorted_keys[i % len(sorted_keys)]
                int_counts[key] += 1

        return int_counts
