"""Tests for PII detector."""

import pytest

from packages.governance_sdk.pii_detector import PIIDetector


class TestPIIDetection:
    """Tests for PII pattern detection."""

    def test_detect_email(self, pii_detector: PIIDetector) -> None:
        """Test email address detection."""
        text = "Contact me at john.doe@example.com for more info."
        matches = pii_detector.detect(text)

        assert len(matches) == 1
        assert matches[0].pii_type == "email"
        assert matches[0].value == "john.doe@example.com"

    def test_detect_phone_number(self, pii_detector: PIIDetector) -> None:
        """Test phone number detection."""
        text = "Call me at (555) 123-4567 or 555-987-6543"
        matches = pii_detector.detect(text)

        assert len(matches) == 2
        assert all(m.pii_type == "phone" for m in matches)

    def test_detect_ssn(self, pii_detector: PIIDetector) -> None:
        """Test SSN detection."""
        text = "My SSN is 123-45-6789"
        matches = pii_detector.detect(text)

        assert len(matches) == 1
        assert matches[0].pii_type == "ssn"

    def test_detect_credit_card(self, pii_detector: PIIDetector) -> None:
        """Test credit card detection."""
        text = "Card number: 4532015112830366"  # Valid Luhn checksum
        matches = pii_detector.detect(text)

        assert len(matches) == 1
        assert matches[0].pii_type == "credit_card"

    def test_detect_multiple_pii_types(self, pii_detector: PIIDetector) -> None:
        """Test detecting multiple PII types in one text."""
        text = "Email: test@example.com, Phone: 555-123-4567, SSN: 123-45-6789"
        matches = pii_detector.detect(text)

        assert len(matches) == 3
        pii_types = {m.pii_type for m in matches}
        assert pii_types == {"email", "phone", "ssn"}

    def test_no_pii_detected(self, pii_detector: PIIDetector) -> None:
        """Test text without PII."""
        text = "This is a normal sentence with no personal information."
        matches = pii_detector.detect(text)

        assert len(matches) == 0


class TestPIIRedaction:
    """Tests for PII redaction."""

    def test_redact_email(self, pii_detector: PIIDetector) -> None:
        """Test redacting email addresses."""
        text = "Contact john.doe@example.com for details."
        redacted = pii_detector.redact(text)

        assert "john.doe@example.com" not in redacted
        assert "[REDACTED]" in redacted

    def test_redact_multiple_pii(self, pii_detector: PIIDetector) -> None:
        """Test redacting multiple PII instances."""
        text = "Email: test@example.com, Phone: 555-123-4567"
        redacted = pii_detector.redact(text)

        assert "test@example.com" not in redacted
        assert "555-123-4567" not in redacted
        assert redacted.count("[REDACTED]") == 2

    def test_custom_replacement(self, pii_detector: PIIDetector) -> None:
        """Test custom redaction replacement."""
        text = "Email: test@example.com"
        redacted = pii_detector.redact(text, replacement="***")

        assert "test@example.com" not in redacted
        assert "***" in redacted


class TestPIIConfidence:
    """Tests for PII detection confidence scores."""

    def test_email_confidence(self, pii_detector: PIIDetector) -> None:
        """Test email detection confidence."""
        text = "test@gmail.com"
        matches = pii_detector.detect(text)

        assert len(matches) == 1
        # Common domain should have higher confidence
        assert matches[0].confidence > 0.8

    def test_credit_card_luhn_validation(self, pii_detector: PIIDetector) -> None:
        """Test credit card Luhn algorithm validation affects confidence."""
        valid_card = "4532015112830366"  # Valid Luhn
        invalid_card = "4532015112830367"  # Invalid Luhn

        valid_matches = pii_detector.detect(valid_card)
        invalid_matches = pii_detector.detect(invalid_card)

        assert len(valid_matches) == 1
        assert len(invalid_matches) == 1
        assert valid_matches[0].confidence > invalid_matches[0].confidence
