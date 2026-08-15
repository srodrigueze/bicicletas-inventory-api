from fastapi import APIRouter, HTTPException, status

from app.api.deps import BicycleServiceDep
from app.schemas.bicycle import BicycleCreate, BicycleRead, BicycleUpdate

router = APIRouter(prefix="/bicycles", tags=["bicycles"])


@router.get("/", response_model=list[BicycleRead])
def list_bicycles(service: BicycleServiceDep):
    return service.list_bicycles()


@router.get("/{bicycle_id}", response_model=BicycleRead)
def get_bicycle(bicycle_id: int, service: BicycleServiceDep):
    bicycle = service.get_bicycle(bicycle_id)
    if not bicycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bicycle not found")
    return bicycle


@router.post("/", response_model=BicycleRead, status_code=status.HTTP_201_CREATED)
def create_bicycle(data: BicycleCreate, service: BicycleServiceDep):
    try:
        return service.create_bicycle(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/{bicycle_id}", response_model=BicycleRead)
def update_bicycle(bicycle_id: int, data: BicycleUpdate, service: BicycleServiceDep):
    bicycle = service.update_bicycle(bicycle_id, data)
    if not bicycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bicycle not found")
    return bicycle


@router.delete("/{bicycle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bicycle(bicycle_id: int, service: BicycleServiceDep):
    service.delete_bicycle(bicycle_id)
