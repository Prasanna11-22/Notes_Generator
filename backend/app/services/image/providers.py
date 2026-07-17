"""
Wikimedia Commons Image Provider Implementation.
"""

import re
from typing import Any, Dict, List
from loguru import logger
import httpx

from app.services.image.provider_base import ImageProvider


class WikimediaProvider(ImageProvider):
    """
    Client strategy retrieving educational diagrams from Wikimedia Commons.
    """

    API_URL = "https://commons.wikimedia.org/w/api.php"

    def get_provider_name(self) -> str:
        return "Wikimedia"

    async def search_images(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Query Wikimedia Commons for file candidates.
        """
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,  # Namespace 6 maps to Commons File: namespace
            "prop": "imageinfo",
            "iiprop": "url|size|extmetadata",
            "format": "json",
            "gsrlimit": limit,
        }
        headers = {
            "User-Agent": "NotesGeneratorEducationalDiagramSearch/1.0 (prasanna@university.edu)"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.API_URL, params=params, headers=headers)
                if response.status_code != 200:
                    logger.warning(
                        "WikimediaProvider | API returned status code: {} for query: {}",
                        response.status_code,
                        query,
                    )
                    return []

                data = response.json()
                query_data = data.get("query")
                if not query_data or "pages" not in query_data:
                    logger.info("WikimediaProvider | No results found for query: {}", query)
                    return []

                pages = query_data["pages"]
                results = []

                for page_id, info in pages.items():
                    imageinfo_list = info.get("imageinfo", [])
                    if not imageinfo_list:
                        continue
                    
                    imageinfo = imageinfo_list[0]
                    url = imageinfo.get("url")
                    if not url:
                        continue

                    # Extract metadata fields
                    extmetadata = imageinfo.get("extmetadata", {})
                    license_val = extmetadata.get("LicenseShortName", {}).get("value", "Unknown")
                    description_val = extmetadata.get("ImageDescription", {}).get("value", "")

                    # Strip HTML formatting tags from wiki descriptions
                    clean_desc = re.sub(r"<[^<]+?>", "", description_val).strip() if description_val else ""

                    results.append({
                        "title": info.get("title", ""),
                        "url": url,
                        "description": clean_desc,
                        "width": imageinfo.get("width", 0),
                        "height": imageinfo.get("height", 0),
                        "license": license_val,
                        "source": "Wikimedia Commons",
                        "thumbnail": imageinfo.get("descriptionurl", url),
                    })

                return results

        except httpx.HTTPError as exc:
            logger.warning(
                "WikimediaProvider | HTTP communication error occurred: {} for query: {}",
                str(exc),
                query,
            )
            return []
        except Exception as exc:
            logger.error(
                "WikimediaProvider | Unexpected error querying Wikimedia API: {} for query: {}",
                str(exc),
                query,
            )
            return []
