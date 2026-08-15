from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.core.database import get_session
from app.infrastructure.repositories.bicycle_repository_sql import SqlBicycleRepository
from app.infrastructure.repositories.loan_repository_sql import SqlLoanRepository
from app.services.bicycle_service import BicycleService
from app.services.loan_service import LoanService

SessionDep = Annotated[Session, Depends(get_session)]


def get_bicycle_repository(session: SessionDep) -> SqlBicycleRepository:
    return SqlBicycleRepository(session)


def get_loan_repository(session: SessionDep) -> SqlLoanRepository:
    return SqlLoanRepository(session)


BicycleRepositoryDep = Annotated[SqlBicycleRepository, Depends(get_bicycle_repository)]
LoanRepositoryDep = Annotated[SqlLoanRepository, Depends(get_loan_repository)]


def get_bicycle_service(
    bicycle_repository: BicycleRepositoryDep,
    loan_repository: LoanRepositoryDep,
) -> BicycleService:
    return BicycleService(bicycle_repository, loan_repository)


def get_loan_service(
    loan_repository: LoanRepositoryDep,
    bicycle_repository: BicycleRepositoryDep,
) -> LoanService:
    return LoanService(loan_repository, bicycle_repository)


BicycleServiceDep = Annotated[BicycleService, Depends(get_bicycle_service)]
LoanServiceDep = Annotated[LoanService, Depends(get_loan_service)]
