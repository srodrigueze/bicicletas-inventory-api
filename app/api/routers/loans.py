from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.api.deps import LoanServiceDep
from app.schemas.loan import LoanCreate, LoanRead, LoanReturn

router = APIRouter(prefix="/loans", tags=["loans"])


@router.get("/", response_model=list[LoanRead])
def list_loans(service: LoanServiceDep):
    return service.list_loans()


@router.get("/{loan_id}", response_model=LoanRead)
def get_loan(loan_id: int, service: LoanServiceDep):
    loan = service.get_loan(loan_id)
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    return loan


@router.post("/", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
def create_loan(data: LoanCreate, service: LoanServiceDep):
    try:
        return service.create_loan(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{loan_id}/return", response_model=LoanRead)
def return_loan(loan_id: int, data: LoanReturn, service: LoanServiceDep):
    return_datetime = data.return_datetime or datetime.now(timezone.utc)
    loan = service.return_loan(loan_id, return_datetime)
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    return loan
