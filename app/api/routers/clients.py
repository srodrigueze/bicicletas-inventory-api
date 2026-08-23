from fastapi import APIRouter, HTTPException, status

from app.api.deps import ClientServiceDep, CurrentUserDep
from app.schemas.client import ClientRead

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/by-document/{document}", response_model=ClientRead)
def get_client_by_document(document: str, current_user: CurrentUserDep, service: ClientServiceDep):
    client = service.get_by_document(document)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client
