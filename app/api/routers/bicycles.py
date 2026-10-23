from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.api.deps import BicycleServiceDep, CurrentUserDep
from app.domain.entities.bicycle import BicycleCondition, BicycleSize
from app.schemas.bicycle import BicycleCreate, BicycleRead, BicycleUpdate

router = APIRouter(prefix="/bicycles", tags=["bicycles"])

_ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024


def _detect_image_type(content: bytes) -> tuple[str, str] | None:
    """Identifies the real format from the file's magic bytes, since the
    Content-Type header and the filename are both chosen by the client.
    Returns (content_type, extension), or None if it isn't an allowed image."""
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


@router.get("/", response_model=list[BicycleRead])
def list_bicycles(
    current_user: CurrentUserDep,
    service: BicycleServiceDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    code: str | None = Query(default=None),
    size: BicycleSize | None = Query(default=None),
    condition: BicycleCondition | None = Query(default=None),
    rueditas_asistencia: bool | None = Query(default=None),
    tiene_pedales: bool | None = Query(default=None),
    numero_frenos: int | None = Query(default=None, ge=0, le=2),
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
        numero_frenos=numero_frenos,
        en_posesion_jac=en_posesion_jac,
    )


@router.get("/{bicycle_id}", response_model=BicycleRead)
def get_bicycle(bicycle_id: int, current_user: CurrentUserDep, service: BicycleServiceDep):
    bicycle = service.get_bicycle(bicycle_id)
    if not bicycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bicycle not found")
    return bicycle


@router.post("/", response_model=BicycleRead, status_code=status.HTTP_201_CREATED)
def create_bicycle(data: BicycleCreate, current_user: CurrentUserDep, service: BicycleServiceDep):
    try:
        return service.create_bicycle(current_user, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/{bicycle_id}", response_model=BicycleRead)
def update_bicycle(bicycle_id: int, data: BicycleUpdate, current_user: CurrentUserDep, service: BicycleServiceDep):
    try:
        bicycle = service.update_bicycle(current_user, bicycle_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not bicycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bicycle not found")
    return bicycle


@router.delete("/{bicycle_id}", response_model=BicycleRead)
def delete_bicycle(bicycle_id: int, current_user: CurrentUserDep, service: BicycleServiceDep):
    bicycle = service.delete_bicycle(current_user, bicycle_id)
    if not bicycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bicycle not found")
    return bicycle


@router.patch("/{bicycle_id}/restore", response_model=BicycleRead)
def restore_bicycle(bicycle_id: int, current_user: CurrentUserDep, service: BicycleServiceDep):
    bicycle = service.restore_bicycle(current_user, bicycle_id)
    if not bicycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bicycle not found")
    return bicycle


@router.post("/{bicycle_id}/image", response_model=BicycleRead)
def upload_bicycle_image(
    bicycle_id: int,
    current_user: CurrentUserDep,
    service: BicycleServiceDep,
    file: UploadFile = File(...),
):
    if file.content_type not in _ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only image/jpeg, image/png or image/webp files are allowed",
        )
    # One byte past the limit is enough to know it's too big, without
    # loading an arbitrarily large body into memory.
    content = file.file.read(_MAX_IMAGE_SIZE_BYTES + 1)
    if len(content) > _MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Image must be at most 5MB",
        )
    detected = _detect_image_type(content)
    if detected is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The file content is not a valid jpeg, png or webp image",
        )
    content_type, extension = detected
    # Stored under a name built from the detected format, never the client's filename.
    bicycle = service.upload_image(current_user, bicycle_id, f"imagen{extension}", content, content_type)
    if not bicycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bicycle not found")
    return bicycle
