"""
License Validation Service for Open Educational Resources (OER).
"""

import re
from loguru import logger


class LicenseValidationService:
    """
    Enforces OER copyright and copyleft open-license policies.
    """

    ALLOWED_LICENSES = {"CC0", "CC BY", "CC BY-SA", "Public Domain"}

    @classmethod
    def normalize_license(cls, raw_license: str) -> str:
        """
        Normalize raw license strings from API providers to standard categories.
        """
        if not raw_license:
            return "Unknown"

        clean = raw_license.strip().upper()

        # Public Domain matches
        if any(term in clean for term in ("PUBLIC DOMAIN", "PUBLICDOMAIN", "PD")):
            return "Public Domain"

        # CC0 matches
        if any(term in clean for term in ("CC0", "CC-ZERO", "CC ZERO")):
            return "CC0"

        # CC BY-SA matches
        if "BY-SA" in clean or "BY SA" in clean:
            return "CC BY-SA"

        # CC BY matches (must not contain SA, ND, NC)
        if "BY" in clean and not any(term in clean for term in ("SA", "ND", "NC")):
            return "CC BY"

        return raw_license

    @classmethod
    def is_license_valid(cls, license_name: str) -> bool:
        """
        Check if normalized license category is allowed for educational redistribution.
        """
        normalized = cls.normalize_license(license_name)
        is_valid = normalized in cls.ALLOWED_LICENSES
        
        if not is_valid:
            logger.info(
                "LicenseValidationService | Rejected license: {} (normalized: {})",
                license_name,
                normalized,
            )
        return is_valid
