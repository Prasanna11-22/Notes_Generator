"""
Image Ranking and Scoring Service.
"""

from typing import Any, Dict, List
from app.services.image.license_validator import LicenseValidationService


class ImageRankingService:
    """
    Computes educational value scores for candidate images to select the highest-quality match.
    """

    @classmethod
    def score_image(cls, candidate: Dict[str, Any], topic: str, preferred_diagram: str) -> float:
        """
        Calculate score out of 100.0 for a candidate image dictionary.
        """
        score = 0.0
        
        title_lower = candidate.get("title", "").lower()
        desc_lower = candidate.get("description", "").lower()
        topic_lower = topic.lower()
        pref_lower = preferred_diagram.lower()

        # 1. Topic Keyword Match (Max 30 points)
        topic_words = [w for w in topic_lower.split() if len(w) > 3]
        if topic_words:
            matched_words = 0
            for word in topic_words:
                if word in title_lower or word in desc_lower:
                    matched_words += 1
            ratio = matched_words / len(topic_words)
            score += ratio * 30.0

        # 2. Preferred Diagram Type Match (Max 20 points)
        if pref_lower in title_lower or pref_lower in desc_lower:
            score += 20.0
        elif "diagram" in title_lower or "diagram" in desc_lower:
            score += 10.0  # partial credit for general diagram keywords

        # 3. Resolution (Max 20 points)
        width = candidate.get("width", 0)
        height = candidate.get("height", 0)
        if width >= 1200:
            score += 20.0
        elif width >= 800:
            score += 15.0
        elif width >= 400:
            score += 5.0

        # 4. Aspect Ratio standard landscape bonus (Max 15 points)
        if width > 0 and height > 0:
            aspect = width / height
            if 1.2 <= aspect <= 1.8:
                score += 15.0
            elif 0.8 <= aspect < 1.2:
                score += 5.0  # square-ish images

        # 5. License Quality (Max 10 points)
        norm_license = LicenseValidationService.normalize_license(candidate.get("license", ""))
        if norm_license in ("CC0", "Public Domain"):
            score += 10.0
        elif norm_license in ("CC BY", "CC BY-SA"):
            score += 5.0

        # 6. Metadata Completeness (Max 5 points)
        if candidate.get("description"):
            score += 3.0
        if candidate.get("title"):
            score += 2.0

        return min(100.0, score)

    @classmethod
    def rank_candidates(cls, candidates: List[Dict[str, Any]], topic: str, preferred_diagram: str) -> List[Dict[str, Any]]:
        """
        Score and sort candidates in descending order.
        """
        for item in candidates:
            item["ranking_score"] = cls.score_image(item, topic, preferred_diagram)

        # Sort by score descending, then by resolution descending
        return sorted(
            candidates,
            key=lambda x: (x.get("ranking_score", 0.0), x.get("width", 0)),
            reverse=True,
        )
