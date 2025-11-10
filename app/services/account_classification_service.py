"""Backward-compatible entry for the new classification orchestrator."""

from app.services.account_classification.orchestrator import AccountClassificationService

__all__ = ["AccountClassificationService"]

# Optional shared instance for legacy usage
account_classification_service = AccountClassificationService()
