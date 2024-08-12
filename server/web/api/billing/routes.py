"""Billings API"""
from typing import Annotated
from fastapi import APIRouter, Depends, Request, HTTPException, status

from server.web.api.billing.service import BillingService
from server.web.api.billing.dto import BalanceBillDTO, CheckBillDTO


api_router = APIRouter()

@api_router.post(
    "/balance",
    tags=["billings"],
    summary="Check if the user can perform the requested action"
)
async def balance_bill(
    req: Request,
    body: BalanceBillDTO,
    billing_service: Annotated[BillingService, Depends(BillingService, use_cache=True)]
) -> None:
    """
    Check if the user has sufficient balance to perform the requested action.

    Parameters:
    req (Request): The FastAPI Request object, which contains information about the incoming request.
    body (BalanceBillDTO): The request body containing the necessary data for balance checking.
    billing_service (BillingService): An instance of the BillingService class, used to perform balance checking.

    Returns:
    bool: A boolean value indicating whether the user has sufficient balance (True) or not (False).
    """
    user_id = req.state.user_id
    bb = await billing_service.balance(body, user_id)
    if bb is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User can not perform this operation")


@api_router.post(
    "/check",
    tags=["billings"],
    summary="Check the bill for a specific action"
)
async def check_bill(
    req: Request,
    body: CheckBillDTO,
    billing_service: Annotated[BillingService, Depends(BillingService, use_cache=True)]
) -> None:
    """
    Checkout the user's action and billthe user

    Parameters:
    req (Request): The FastAPI Request object, which contains information about the incoming request.
    body (CheckBillDTO): The request body containing the necessary data for checking the bill.
    billing_service (BillingService): An instance of the BillingService class, used to perform bill checking.

    Returns:
    None: The function does not return any value.
    """
    user_id = req.state.user_id
    await billing_service.check(body, user_id)
