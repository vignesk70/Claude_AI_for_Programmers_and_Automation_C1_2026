from enum import Enum


class TicketCategory(str, Enum):
    """Support ticket categories."""
    DELIVERY = "delivery"
    REFUND = "refund"
    BILLING = "billing"
    PRODUCT = "product"
    ACCOUNT = "account"
    GENERAL = "general"


class Sentiment(str, Enum):
    """Customer sentiment classification."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    ANGRY = "angry"
    FRUSTRATED = "frustrated"


class Priority(str, Enum):
    """Ticket priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
