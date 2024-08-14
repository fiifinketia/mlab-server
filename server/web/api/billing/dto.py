from pydantic import BaseModel
from typing import Any

from server.db.models.billings import Action

class BalanceBillDTO(BaseModel):
    """DTO for balance bill."""
    action: Action
    data: Any

class CheckBillDTO(BaseModel):
    """Check bill model."""
    action: Action
    data: Any


class CheckoutResponse(BaseModel):
    """Response model for checkout."""
    user_email: str
    amount: float
