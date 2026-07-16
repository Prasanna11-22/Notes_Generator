"""
Distractor Analyzer Service for MCQ generation choices.
"""

from typing import Dict


class DistractorAnalyzer:
    """
    Analyzes multiple choice distractors to verify plausibility, 
    uniqueness, and prevent obvious giveaways.
    """

    @classmethod
    def analyze_distractors(cls, options: Dict[str, str]) -> None:
        """
        Verify multiple choice distractors meet production-grade guidelines.
        """
        if not options or len(options) < 2:
            return

        # 1. Option uniqueness check
        cleaned_choices = {}
        for key, val in options.items():
            cleaned = " ".join(val.strip().lower().split())
            if cleaned in cleaned_choices.values():
                raise ValueError(
                    f"Distractor analysis failed: Duplicate option choices found. "
                    f"Duplicate text: '{val}'"
                )
            cleaned_choices[key] = cleaned

        # 2. Filter obvious wrong answers or lazy placeholders
        obvious_wrong_patterns = [
            "option", "choice", "placeholder", "n/a", "not applicable", 
            "none of the above", "all of the above"
        ]
        
        for key, val in options.items():
            val_lower = val.lower().strip()
            # If the option matches lazy placeholders or contains the option key verbatim (e.g. choice A)
            for pattern in obvious_wrong_patterns:
                if val_lower == pattern or val_lower == f"{pattern} {key.lower()}":
                    raise ValueError(
                        f"Distractor analysis failed: Found low-quality distractor placeholder "
                        f"'{val}' in option '{key}'."
                    )

            # Check if option contains itself recursively (e.g. Option A value is 'A')
            if val_lower == key.lower():
                raise ValueError(
                    f"Distractor analysis failed: Option choice value is identical to its key index '{key}'."
                )

        # 3. Size balance check (obvious giveaway check)
        # If one option is extremely long/short compared to others (e.g. 5x size difference), it can be a giveaway.
        lengths = [len(v) for v in options.values() if v]
        if lengths:
            max_len = max(lengths)
            min_len = min(lengths)
            # Standard giveaway warning threshold: if one option is 6 times longer than another
            if min_len > 0 and (max_len / min_len) > 6.0:
                # We log this or raise a warning/error depending on strictness
                # Let's raise an error to enforce distractor balance in validation tests.
                raise ValueError(
                    f"Distractor analysis failed: Obvious giveaway detected. Option lengths are unbalanced "
                    f"(max: {max_len} chars, min: {min_len} chars)."
                )
