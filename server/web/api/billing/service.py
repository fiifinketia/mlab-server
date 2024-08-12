"""Billings Service"""
from server.web.api.billing.dto import BalanceBillDTO, Action, CheckBillDTO

class BillingService:

    def __init__(self) -> None:
        pass

    async def balance(self, dto: BalanceBillDTO, user_id: str) -> bool:
        match dto.action:
            case Action.CREATE_DATASET:
                return self._create_project_balance(dto, user_id)
            case Action.CREATE_MODEL:
                return self._create_project_balance(dto, user_id)
            case Action.CREATE_JOB:
                return True
            case Action.STOP_JOB:
                return True
            case Action.CLOSE_JOB:
                return True
            case Action.RUN_JOB:
                return True
            case Action.UPLOAD_TEST_JOB:
                return True
            case _:
                return False

    async def check(self, dto: CheckBillDTO, user_id: str) -> None:
        """Check bill."""
        match dto.action:
            case Action.CREATE_DATASET:
                return self._create_project_check(dto, user_id)
            case Action.CREATE_MODEL:
                return self._create_project_check(dto, user_id)
            case Action.CREATE_JOB:
                pass
            case Action.STOP_JOB:
                pass
            case Action.CLOSE_JOB:
                pass
            case Action.RUN_JOB:
                pass
            case Action.UPLOAD_TEST_JOB:
                pass
            case Action.RUNNER_BILL:
                pass
            case _:
                pass

    def _create_project_balance(self, dto: BalanceBillDTO, user_id: str) -> bool:
        """Create project balance."""
        return True

    def _create_project_check(self, dto: CheckBillDTO, user_id: str) -> None:
        """Create project check."""
        return
