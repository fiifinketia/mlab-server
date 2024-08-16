"""Billings API"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, Request, HTTPException, status

from server.db.models.billings import Billing
from server.web.api.billing.service import BillingService
from server.web.api.billing.dto import BalanceBillDTO, CheckBillDTO, CheckoutResponse


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
    Check the user's action and create bill

    Parameters:
    req (Request): The FastAPI Request object, which contains information about the incoming request.
    body (CheckBillDTO): The request body containing the necessary data for checking the bill.
    billing_service (BillingService): An instance of the BillingService class, used to perform bill checking.

    Returns:
    None: The function does not return any value.
    """
    user_id = req.state.user_id
    await billing_service.check(body, user_id)


@api_router.post(
    "/checkout",
    tags=["billings"],
    summary="Checkout the user's bill"
)
async def checkout_bill(
    req: Request,
    user_email: str,
    billing_service: Annotated[BillingService, Depends(BillingService, use_cache=True)]
) -> CheckoutResponse:
    """
    Checkout the user's bill

    Parameters:
    req (Request): The FastAPI Request object, which contains information about the incoming request.
    user_email (str): The email of the user for which the bill needs to be checked out.
    billing_service (BillingService): An instance of the BillingService class, used to perform bill checkout.
    Returns:
    CheckoutResponse: A response object containing the user's email and total amount for the bill.
    """
    user_id = req.state.user_id
    return await billing_service.checkout(user_id, user_email)

@api_router.get(
    "",
    tags=["billings"],
    summary="Get all billings"
)
async def get_billings(
    req: Request,
    billing_service: Annotated[BillingService, Depends(BillingService, use_cache=True)]
) -> List[Billing]:
    """
    Get all billings

    Parameters:
    req (Request): The FastAPI Request object, which contains information about the incoming request.
    billing_service (BillingService): An instance of the BillingService class, used to retrieve all billings.

    Returns:
    List[Billing]: A list of all billings.
    """
    user_id = req.state.user_id
    return await billing_service.get_billings(user_id)
