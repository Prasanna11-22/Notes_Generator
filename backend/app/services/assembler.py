"""
Context assembler for packaging chunk text and metadata sources.
"""

from app.services.ranking import RetrievalCandidate


class ContextAssembler:
    """
    Service responsible for converting ranked candidates into ordered, formatted context payloads.
    """

    @staticmethod
    def format_chunk_label(candidate: RetrievalCandidate) -> str:
        """
        Generate source identification labels for each text chunk.
        """
        mapping = candidate.mapping
        resource_title = getattr(mapping.resource, "title", "Unknown Document")
        pages = mapping.page_numbers or "N/A"

        parts = [f"Source: {resource_title}", f"Page: {pages}"]

        if mapping.chapter_name:
            parts.append(f"Chapter: {mapping.chapter_name}")
        if mapping.section_heading:
            parts.append(f"Section: {mapping.section_heading}")
        if mapping.bloom_level:
            parts.append(f"Bloom Level: {mapping.bloom_level}")

        return "[" + ", ".join(parts) + "]"

    def assemble(self, query: str, candidates: list[RetrievalCandidate]) -> dict:
        """
        Combine candidates list into a prompt context dictionary package.
        """
        chunks_payload = []
        text_segments = []

        for candidate in candidates:
            mapping = candidate.mapping
            label = self.format_chunk_label(candidate)

            # Build markdown context snippet
            text_segments.append(f"{label}\n{candidate.text}")

            # Build structured payload segment
            chunks_payload.append({
                "chunk_id": candidate.chunk_id,
                "text": candidate.text,
                "score": candidate.score,
                "course_id": mapping.course_id,
                "resource_id": mapping.resource_id,
                "resource_title": getattr(mapping.resource, "title", "Unknown Document"),
                "page_numbers": mapping.page_numbers,
                "chunk_title": mapping.chunk_title,
                "chapter_name": mapping.chapter_name,
                "section_heading": mapping.section_heading,
                "subheading": mapping.subheading,
                "bloom_level": mapping.bloom_level,
                "knowledge_level": mapping.knowledge_level,
                "resource_type": mapping.resource_type,
            })

        formatted_context = "\n\n---\n\n".join(text_segments) if text_segments else ""

        return {
            "query": query,
            "chunks": chunks_payload,
            "formatted_context": formatted_context,
        }
