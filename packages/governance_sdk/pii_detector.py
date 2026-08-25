"""PII detection module for identifying personally identifiable information."""

import re
from dataclasses import dataclass


@dataclass
class PIIMatch:
    """A detected PII match."""

    pii_type: str
    value: str
    start_pos: int
    end_pos: int
    confidence: float


class PIIDetector:
    """
    Detector for identifying personally identifiable information in text.

    This detector uses pattern matching to identify common PII types including
    email addresses, phone numbers, credit cards, SSNs, and custom patterns.
    """

    # Pattern definitions for common PII types
    PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
        "ssn": r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b",
        "credit_card": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b",
        "ip_address": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
    }

    def __init__(self, custom_patterns: dict[str, str] | None = None) -> None:
        """
        Initialize the PII detector.

        Args:
            custom_patterns: Optional dictionary of custom pattern names to regex patterns.
        """
        self.patterns = self.PATTERNS.copy()
        if custom_patterns:
            self.patterns.update(custom_patterns)

        # Compile patterns for efficiency
        self.compiled_patterns = {
            name: re.compile(pattern) for name, pattern in self.patterns.items()
        }

    def detect(self, text: str) -> list[PIIMatch]:
        """
        Detect PII in the given text.

        Args:
            text: Text to scan for PII.

        Returns:
            List of PIIMatch objects representing detected PII.
        """
        matches: list[PIIMatch] = []

        for pii_type, pattern in self.compiled_patterns.items():
            for match in pattern.finditer(text):
                matches.append(
                    PIIMatch(
                        pii_type=pii_type,
                        value=match.group(),
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=self._calculate_confidence(pii_type, match.group()),
                    )
                )

        return matches

    def redact(self, text: str, replacement: str = "[REDACTED]") -> str:
        """
        Redact all detected PII from text.

        Args:
            text: Text to redact PII from.
            replacement: String to replace PII with.

        Returns:
            Text with PII redacted.
        """
        result = text
        # Sort matches by position in reverse order to avoid offset issues
        matches = sorted(self.detect(text), key=lambda m: m.start_pos, reverse=True)

        for match in matches:
            result = result[: match.start_pos] + replacement + result[match.end_pos :]

        return result

    def has_pii(self, text: str) -> bool:
        """
        Check if text contains any PII.

        Args:
            text: Text to check.

        Returns:
            True if PII is detected, False otherwise.
        """
        return len(self.detect(text)) > 0

    def _calculate_confidence(self, pii_type: str, value: str) -> float:
        """
        Calculate confidence score for a PII match.

        Args:
            pii_type: Type of PII detected.
            value: The matched value.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        # Simple heuristic-based confidence scoring
        # In production, this could be enhanced with ML models

        if pii_type == "email":
            # Check for common domains to reduce false positives
            common_domains = [
                "gmail.com",
                "yahoo.com",
                "outlook.com",
                "hotmail.com",
            ]
            return 0.95 if any(domain in value for domain in common_domains) else 0.85

        elif pii_type == "credit_card":
            # Validate using Luhn algorithm
            return 0.95 if self._luhn_check(value) else 0.70

        elif pii_type == "ssn":
            return 0.90

        elif pii_type == "phone":
            return 0.85

        return 0.75

    def _luhn_check(self, card_number: str) -> bool:
        """
        Validate credit card number using Luhn algorithm.

        Args:
            card_number: Card number to validate.

        Returns:
            True if valid, False otherwise.
        """
        digits = [int(d) for d in card_number if d.isdigit()]
        checksum = 0

        # Double every second digit from right to left
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0
