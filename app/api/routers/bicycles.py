from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import BicycleServiceDep
from app.domain.entities.bicycle import BicycleCondition, BicycleSize
from app.schemas.bicycle import BicycleCreate, BicycleRead, BicycleUpdate

router = APIRouter(prefix="/bicycles", tags=["bicycles"])


@router.get("/", response_model=list[BicycleRead])
def list_bicycles(
    service: BicycleServiceDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    code: str | None = Query(default=None),
    size: BicycleSize | None = Query(default=None),
    condition: BicycleCondition | None = Query(default=None),
    rueditas_asistencia: bool | None = Query(default=None),
    tiene_pedales: bool | None = Query(default=None),
    en_posesion_jac: bool | None = Query(default=None),
):
    return service.list_bicycles(
        skip=skip,
        limit=limit,
        code=code,
        size=size,
        condition=condition,
        rueditas_asistencia=rueditas_asistencia,
        tiene_pedales=tiene_pedales,
        en_posesion_jac=en_posesion_jac,
    )


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
    try:
        bicycle = service.update_bicycle(bicycle_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not bicycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bicycle not found")
    return bicycle


@router.delete("/{bicycle_id}", response_model=BicycleRead)
def delete_bicycle(bicycle_id: int, service: BicycleServiceDep):
    bicycle = service.delete_bicycle(bicycle_id)
    if not bicycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bicycle not found")
    return bicycle


@router.patch("/{bicycle_id}/restore", response_model=BicycleRead)
def restore_bicycle(bicycle_id: int, service: BicycleServiceDep):
    bicycle = service.restore_bicycle(bicycle_id)
    if not bicycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bicycle not found")
    return bicycle
