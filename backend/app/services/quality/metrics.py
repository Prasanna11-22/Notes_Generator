"""
Readability Analysis and Consistency Validation Services.
"""

import re
from typing import List


class ReadabilityAnalysisService:
    """
    Measures sentence length, paragraph distribution, heading hierarchy, and reading ease grades.
    """

    @classmethod
    def count_syllables_in_word(cls, word: str) -> int:
        """
        Heuristic vowel-counter to calculate syllables per word.
        """
        word = word.lower().strip()
        if not word:
            return 0
        vowels = "aeiouy"
        count = 0
        prev_is_vowel = False
        for char in word:
            is_v = char in vowels
            if is_v and not prev_is_vowel:
                count += 1
            prev_is_vowel = is_v
        if word.endswith("e") and count > 1:
            count -= 1
        return max(1, count)

    @classmethod
    def analyze_readability(cls, content: str) -> dict:
        """
        Compute sentence count, word count, Flesch Reading Ease score, and readability grade.
        """
        sentences = [s.strip() for s in re.split(r"[.!?]+", content) if s.strip()]
        words = [w.strip() for w in re.split(r"\s+", content) if w.strip()]
        
        sentence_count = max(1, len(sentences))
        word_count = max(1, len(words))

        # Sum syllables
        total_syllables = sum(cls.count_syllables_in_word(w) for w in words)

        # Flesch Reading Ease Formula
        asl = word_count / sentence_count
        asw = total_syllables / word_count
        flesch_score = 206.835 - 1.015 * asl - 84.6 * asw
        flesch_score = max(0.0, min(100.0, flesch_score))

        # Map Flesch Reading Ease score to Grade Levels
        if flesch_score >= 90.0:
            level = "5th Grade (Very Easy)"
        elif flesch_score >= 80.0:
            level = "6th Grade (Easy)"
        elif flesch_score >= 70.0:
            level = "7th Grade (Fairly Easy)"
        elif flesch_score >= 60.0:
            level = "8th-9th Grade (Standard)"
        elif flesch_score >= 50.0:
            level = "10th-12th Grade (Fairly Difficult)"
        elif flesch_score >= 30.0:
            level = "College (Difficult)"
        else:
            level = "College Graduate (Very Difficult/Technical)"

        # Heading structure check (markdown headings count)
        headings = re.findall(r"^(#+)\s+(.+)$", content, re.MULTILINE)
        has_headings = len(headings) > 0
        heading_levels = [len(h[0]) for h in headings]
        
        # Verify heading hierarchy: H1 should not be skipped, H3 shouldn't follow H1 directly
        heading_hierarchy_ok = True
        for i in range(1, len(heading_levels)):
            if heading_levels[i] > heading_levels[i-1] + 1:
                heading_hierarchy_ok = False
                break

        return {
            "score": flesch_score,
            "reading_ease": flesch_score,
            "reading_level": level,
            "metrics": {
                "total_words": word_count,
                "total_sentences": sentence_count,
                "average_sentence_length": asl,
                "average_syllables_per_word": asw,
                "total_headings": len(headings),
                "headings_hierarchy_valid": heading_hierarchy_ok,
            }
        }


class ConsistencyValidationService:
    """
    Checks generated texts for conceptual repetitions, paragraph redundancy, and broken anchors.
    """

    @classmethod
    def detect_duplicate_paragraphs(cls, content: str, threshold: float = 0.6) -> dict:
        """
        Split text by double newlines and compute Jaccard similarities to flag repetitions.
        """
        paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 30]
        duplicates = []

        for i in range(len(paragraphs)):
            words_a = set(re.findall(r"\w+", paragraphs[i].lower()))
            if not words_a:
                continue
            for j in range(i + 1, len(paragraphs)):
                words_b = set(re.findall(r"\w+", paragraphs[j].lower()))
                if not words_b:
                    continue
                intersection = words_a.intersection(words_b)
                union = words_a.union(words_b)
                jaccard = len(intersection) / len(union)
                if jaccard >= threshold:
                    duplicates.append({
                        "index_a": i,
                        "index_b": j,
                        "similarity": jaccard,
                        "snippet": paragraphs[i][:60] + "...",
                    })

        passed = len(duplicates) == 0
        # Calculate a penalty score
        score = max(0.0, 100.0 - len(duplicates) * 20.0)

        return {
            "passed": passed,
            "score": score,
            "details": {
                "total_paragraphs_evaluated": len(paragraphs),
                "redundancies_detected_count": len(duplicates),
                "duplicates_list": duplicates,
            }
        }

    @classmethod
    def detect_inconsistencies(cls, content: str) -> dict:
        """
        Look for common indicator contradictions or broken links/references in text.
        """
        content_lower = content.lower()
        contradictions = []
        
        # Simple phrase checks
        contradiction_patterns = [
            (r"however, it is not.*although it is", "Potential conditional contradiction"),
            (r"unlike (\w+), which is \w+.*like \1, which is \w+", "Potential comparator contradiction"),
        ]

        for pattern, msg in contradiction_patterns:
            if re.search(pattern, content_lower):
                contradictions.append(msg)

        # Check for broken references (e.g. "see section X" or "refer to Table Y" where they don't exist)
        broken_references = []
        ref_matches = re.findall(r"(?:see|refer to)\s+(?:section|table|figure)\s+(\w+)", content_lower)
        for ref in ref_matches:
            # Check if reference tag matches a heading or anchor text in the document
            pattern = rf"(?:#+|\*\*|__|\b{ref}:)\s*{ref}"
            if not re.search(pattern, content_lower):
                broken_references.append(f"Broken cross-reference target: {ref}")

        passed = len(contradictions) == 0 and len(broken_references) == 0
        score = max(0.0, 100.0 - (len(contradictions) + len(broken_references)) * 25.0)

        return {
            "passed": passed,
            "score": score,
            "details": {
                "contradictions_found": contradictions,
                "broken_references_found": broken_references,
            }
        }
