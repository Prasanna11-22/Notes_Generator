"""
Keyword and Educational Concept Extraction Service.
"""

from typing import List, Dict, Any


class EducationalConceptExtractor:
    """
    Extracts educational concepts (algorithms, protocols, math, science)
    and maps them to preferred diagram formats.
    """

    # Educational taxonomies for heuristic mapping
    ALGORITHMS = {"search", "sort", "tree", "graph", "binary", "recursion", "dijkstra", "traversal"}
    PROTOCOLS = {"tcp", "udp", "ip", "http", "dns", "dhcp", "network", "packet", "socket"}
    MATHEMATICS = {"matrix", "vector", "limit", "derivative", "integral", "geometry", "probability", "statistics"}
    SCIENCE = {"cell", "photosynthesis", "atom", "molecule", "chemical", "physics", "gravity", "energy"}
    PROGRAMMING = {"class", "object", "inheritance", "polymorphism", "variable", "function", "pointer", "memory"}

    @classmethod
    def analyze_concept(cls, topic: str, description: str = "") -> Dict[str, Any]:
        """
        Analyze a topic name and optional description to extract categories
        and determine a preferred diagram format.
        """
        text = f"{topic} {description}".lower()

        primary_concept = topic.strip()
        secondary_concepts = []
        category = "General"
        preferred_diagram = "Diagram"

        # Determine Category & Preferred Diagram Type
        if any(word in text for word in cls.ALGORITHMS):
            category = "Algorithm"
            preferred_diagram = "Flowchart"
        elif any(word in text for word in cls.PROTOCOLS):
            category = "Network Protocol"
            preferred_diagram = "Network Diagram"
        elif any(word in text for word in cls.MATHEMATICS):
            category = "Mathematical Concept"
            preferred_diagram = "Graph"
        elif any(word in text for word in cls.SCIENCE):
            category = "Scientific Term"
            preferred_diagram = "Illustration"
        elif any(word in text for word in cls.PROGRAMMING):
            category = "Programming Concept"
            preferred_diagram = "Architecture Diagram"

        # Extract secondary concepts (heuristics on multi-word strings)
        words = text.split()
        for w in words:
            w_clean = "".join(filter(str.isalnum, w))
            if len(w_clean) > 4 and w_clean != primary_concept.lower():
                if w_clean in cls.ALGORITHMS or w_clean in cls.PROTOCOLS or w_clean in cls.SCIENCE:
                    secondary_concepts.append(w_clean.capitalize())

        return {
            "primary_concept": primary_concept,
            "secondary_concepts": list(set(secondary_concepts)),
            "category": category,
            "preferred_diagram": preferred_diagram,
        }


class KeywordExtractionService:
    """
    Optimizes extracted educational concepts into search queries.
    """

    @classmethod
    def extract_optimized_queries(cls, topic: str, description: str = "") -> List[str]:
        """
        Convert a topic and description into a prioritized list of search queries.
        """
        analysis = EducationalConceptExtractor.analyze_concept(topic, description)
        concept = analysis["primary_concept"]
        pref_diagram = analysis["preferred_diagram"]

        # Formulate optimized query candidates in order of search specificity
        queries = [
            f"{concept} {pref_diagram}",
            f"{concept} Diagram",
            f"{concept} Flowchart",
            f"{concept} Visualization",
            f"{concept} Illustration",
        ]

        # Return unique ordered list
        seen = set()
        unique_queries = []
        for q in queries:
            q_clean = " ".join(q.split())
            if q_clean not in seen:
                seen.add(q_clean)
                unique_queries.append(q_clean)

        return unique_queries
