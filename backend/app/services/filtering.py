"""
Metadata filter service for evaluating and applying metadata search constraints.
"""

from datetime import datetime
from uuid import UUID
from app.models.chunk import ChunkMapping


class MetadataFilter:
    """
    Service responsible for applying filtering criteria to ChunkMapping candidates.
    """

    @staticmethod
    def match(mapping: ChunkMapping, criteria: dict) -> bool:
        """
        Check if a given ChunkMapping matches filter criteria.
        Criteria is passed as a dictionary containing non-null constraints.
        """
        if not criteria:
            return True

        # Course filter
        if "course_id" in criteria and criteria["course_id"]:
            if mapping.course_id != criteria["course_id"]:
                return False

        # Unit filter
        if "unit_id" in criteria and criteria["unit_id"]:
            if mapping.unit_id != criteria["unit_id"]:
                return False

        # Topic filter
        if "topic_id" in criteria and criteria["topic_id"]:
            if mapping.topic_id != criteria["topic_id"]:
                return False

        # Resource ID / Document filter
        if "resource_id" in criteria and criteria["resource_id"]:
            if mapping.resource_id != criteria["resource_id"]:
                return False

        # Uploaded by / Faculty filter
        if "uploaded_by" in criteria and criteria["uploaded_by"]:
            uploaded_by = getattr(mapping.resource, "uploaded_by", None)
            if uploaded_by != criteria["uploaded_by"]:
                return False

        # Resource type (checks mapping, falls back to resource)
        if "resource_type" in criteria and criteria["resource_type"]:
            val = mapping.resource_type or getattr(mapping.resource, "resource_type", "")
            if not val or val.lower() != criteria["resource_type"].lower():
                return False

        # Bloom level
        if "bloom_level" in criteria and criteria["bloom_level"]:
            val = mapping.bloom_level
            if not val or val.lower() != criteria["bloom_level"].lower():
                return False

        # Knowledge level
        if "knowledge_level" in criteria and criteria["knowledge_level"]:
            val = mapping.knowledge_level
            if not val or val.lower() != criteria["knowledge_level"].lower():
                return False

        # Difficulty
        if "difficulty" in criteria and criteria["difficulty"]:
            val = getattr(mapping, "difficulty", None)
            if not val or str(val).lower() != criteria["difficulty"].lower():
                return False

        # Created after date boundary
        if "created_after" in criteria and criteria["created_after"]:
            # Ensure timezone compatibility
            mapping_dt = mapping.created_at
            after_dt = criteria["created_after"]
            if mapping_dt.tzinfo is not None and after_dt.tzinfo is None:
                # Make aware if naive
                after_dt = after_dt.replace(tzinfo=mapping_dt.tzinfo)
            elif mapping_dt.tzinfo is None and after_dt.tzinfo is not None:
                after_dt = after_dt.replace(tzinfo=None)

            if mapping_dt < after_dt:
                return False

        # Created before date boundary
        if "created_before" in criteria and criteria["created_before"]:
            mapping_dt = mapping.created_at
            before_dt = criteria["created_before"]
            if mapping_dt.tzinfo is not None and before_dt.tzinfo is None:
                before_dt = before_dt.replace(tzinfo=mapping_dt.tzinfo)
            elif mapping_dt.tzinfo is None and before_dt.tzinfo is not None:
                before_dt = before_dt.replace(tzinfo=None)

            if mapping_dt > before_dt:
                return False

        return True

    def filter_mappings(
        self,
        raw_results: list[tuple[ChunkMapping, float]],
        criteria: dict | None,
    ) -> list[tuple[ChunkMapping, float]]:
        """
        Filter search candidates using criteria constraints dictionary.
        """
        if not criteria:
            return raw_results

        # Filter out keys with None values
        clean_criteria = {k: v for k, v in criteria.items() if v is not None}

        filtered = []
        for mapping, dist in raw_results:
            if self.match(mapping, clean_criteria):
                filtered.append((mapping, dist))
        return filtered
