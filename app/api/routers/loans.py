from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUserDep, LoanServiceDep
from app.schemas.loan import LoanAddBicycles, LoanCreate, LoanRead

router = APIRouter(prefix="/loans", tags=["loans"])


@router.get("/", response_model=list[LoanRead])
def list_loans(
    current_user: CurrentUserDep,
    service: LoanServiceDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    active_only: bool = Query(default=True),
    status_filter: Literal["activo", "incumplido", "cerrado"] | None = Query(default=None, alias="status"),
    start_date: date | None = Query(default=None, description="Un solo valor filtra ese día completo"),
    end_date: date | None = Query(default=None),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="start_date must not be after end_date"
        )
    return service.list_loans(
        active_only=active_only,
        skip=skip,
        limit=limit,
        status=status_filter,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/{loan_id}", response_model=LoanRead)
def get_loan(loan_id: int, current_user: CurrentUserDep, service: LoanServiceDep):
    loan = service.get_loan(loan_id)
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    return loan


@router.post("/", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
def create_loan(data: LoanCreate, current_user: CurrentUserDep, service: LoanServiceDep):
    try:
        return service.create_loan(current_user, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{loan_id}/details/{detail_id}/return", response_model=LoanRead)
def return_detail(loan_id: int, detail_id: int, current_user: CurrentUserDep, service: LoanServiceDep):
    try:
        return service.return_detail(current_user, loan_id, detail_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{loan_id}/details", response_model=LoanRead)
def add_bicycles(loan_id: int, data: LoanAddBicycles, current_user: CurrentUserDep, service: LoanServiceDep):
    try:
        return service.add_bicycles(current_user, loan_id, data.bicycle_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{loan_id}/details/{detail_id}/mark-incumplido", response_model=LoanRead)
def mark_incumplido(loan_id: int, detail_id: int, current_user: CurrentUserDep, service: LoanServiceDep):
    try:
        return service.mark_incumplido(current_user, loan_id, detail_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
