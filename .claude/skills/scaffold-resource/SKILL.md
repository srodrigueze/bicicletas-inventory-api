---
name: scaffold-resource
description: Scaffold a new domain resource (entity, repository, service, schema, router) following this project's layered architecture. Use when the user asks to add a new resource/entity/model to the backend, e.g. "add a Station resource", "scaffold a new entity called X".
---

# Scaffold a new resource

Generates a new domain resource end-to-end, replicating the exact pattern already
used for `Bicycle` and `Loan` in this project. Do not invent a different structure —
read the reference files listed below before writing anything.

## 1. Gather requirements

If not already given by the user, ask for:

- **Resource name** (singular, PascalCase for the class, e.g. `Station`).
- **Fields**: name, Python type, required/optional, default value, and any enum
  values (enums are `str, Enum` classes, same style as `BicycleCondition`).
- **Relationships to existing entities**:
  - Simple foreign key (one-to-many) → a plain `Field(foreign_key="other.id")`.
  - Many-to-many → a link table `SQLModel` class (see `LoanBicycleLink` in
    `app/domain/entities/loan.py`) plus a `Relationship(link_model=...)`.
- **Unique field**, if any (e.g. `Bicycle.code`) — determines whether the repository
  needs a `get_by_<field>` method.
- **Derived/computed fields** that should appear in the `Read` schema but are not
  columns (e.g. `Bicycle.is_available`) — these are computed in the service, never
  stored on the entity.

## 2. Reference files (read these first, mirror their structure exactly)

| Layer | Reference file |
|---|---|
| Entity (simple) | `app/domain/entities/bicycle.py` |
| Entity (with relationship/link table) | `app/domain/entities/loan.py` |
| Repository interface | `app/domain/repositories/bicycle_repository.py` |
| Repository SQL implementation | `app/infrastructure/repositories/bicycle_repository_sql.py` |
| Schemas (Create/Update/Read) | `app/schemas/bicycle.py` |
| Service (simple CRUD) | `app/services/bicycle_service.py` |
| Service (derived fields via `_to_read`, cross-repo business rules) | `app/services/loan_service.py` |
| Router | `app/api/routers/bicycles.py` |
| Dependency wiring | `app/api/deps.py` |
| App wiring | `app/main.py` |

## 3. Generate the files

For a resource named `<Name>` (e.g. `Station`, file-name-cased `<name>` = `station`):

1. `app/domain/entities/<name>.py` — `SQLModel` with `table=True`. `id: int | None
   = Field(default=None, primary_key=True)`. Enums as separate `str, Enum` classes.
   If there's a many-to-many relationship, add the link table here too (see
   `LoanBicycleLink`) and use `TYPE_CHECKING` for the forward-referenced entity
   import (see the `if TYPE_CHECKING:` block in `loan.py`).

2. `app/domain/repositories/<name>_repository.py` — `ABC` with `@abstractmethod`
   methods: `get_by_id`, `list_all`, `create`, `update`, `delete`, plus
   `get_by_<unique_field>` if a unique field exists, plus any query the service will
   need for business rules (mirror `list_active_by_bicycle` in
   `app/domain/repositories/loan_repository.py` as an example of a repo method that
   exists purely to support a service-level rule).

3. `app/infrastructure/repositories/<name>_repository_sql.py` — `Sql<Name>Repository`
   implementing the interface above. Constructor takes a `Session`. Use
   `select(...)`/`session.get(...)`/`session.exec(...)`. `create`/`update` both do
   `add` → `commit` → `refresh` → `return`.

4. `app/schemas/<name>.py` — Pydantic `BaseModel`s:
   - `<Name>Create`: required fields for creation, with `Field(..., max_length=...)`
     where the entity has a length constraint.
   - `<Name>Update`: every field optional (`| None = None`), used with
     `exclude_unset=True` in the service for `PATCH`.
   - `<Name>Read`: mirrors the entity's fields plus any derived fields, with
     `model_config = ConfigDict(from_attributes=True)`.

5. `app/services/<name>_service.py` — `<Name>Service` class, constructor takes the
   repository interface(s) it needs (not the SQL implementation — depend on the
   abstraction). Implement `list_<name>s`, `get_<name>`, `create_<name>`,
   `update_<name>`, `delete_<name>`. If there are derived fields or relationships to
   flatten into the `Read` schema, add a private `_to_read(entity) -> <Name>Read`
   helper (see `BicycleService._to_read` / `LoanService._to_read`) and use it
   everywhere instead of relying on `from_attributes` alone. Business rules
   (uniqueness checks, cross-entity validation) raise `ValueError` with a clear
   message — never `HTTPException` here, that belongs in the router.

6. `app/api/routers/<name>s.py` — `APIRouter(prefix="/<name>s", tags=["<name>s"])`
   with `GET /`, `GET /{id}`, `POST /`, `PATCH /{id}`, `DELETE /{id}`. Catch
   `ValueError` from the service and re-raise as `HTTPException(status_code=409,
   detail=str(exc))`; missing resource → `HTTPException(status_code=404)`.

## 4. Wire it up

- `app/api/deps.py`: add `get_<name>_repository` and `get_<name>_service` functions
  plus their `Annotated[..., Depends(...)]` type aliases, following the existing
  `BicycleRepositoryDep`/`BicycleServiceDep` pattern.
- `app/main.py`: `from app.api.routers import <name>s` and
  `app.include_router(<name>s.router)`.

## 5. Remind the user of the manual next steps

This skill does **not** run Alembic. After generating the files, tell the user to:

```bash
alembic revision --autogenerate -m "add <name> table"
```

and to **check the generated file for a missing `import sqlmodel`**, and for missing
`CREATE TYPE`/`DROP TYPE` statements if the entity has enum columns, before running
`alembic upgrade head` — Alembic's autogenerate does not always add these on its own.
This exact bug happened when `bicycle`/`loan`/`user` were first migrated (see
`migrations/versions/77df9202930e_*.py` and `73b20e845bca_*.py`).

This skill also does **not** write tests — scaffolding covers the CRUD skeleton, not
its test coverage. Remind the user that once the business rules for `<name>` are
implemented (via the `desarrollador-tester` vault workflow, if the resource maps to a
documented `REQ-xxx`), the corresponding `tests/test_<name>s.py` needs its own test
per test case, following the fixtures already in `tests/conftest.py` (`client`,
`make_user`, `token_for`) and the pattern in `tests/test_auth.py`.

## Conventions to always follow

- All code in English (class names, field names, file names) — even though the
  public-facing UI/API may speak Spanish later.
- Synchronous SQLModel sessions (`Session`, not `AsyncSession`) — the whole project
  is sync.
- Derived (non-column) fields are computed in the service and passed explicitly into
  the `Read` schema constructor (`Schema(**entity.model_dump(), derived_field=...)`).
  Never add fake attributes to the SQLModel entity to make `from_attributes` work.
- Router file names are plural (`bicycles.py`, `loans.py`); entity file names are
  singular (`bicycle.py`, `loan.py`).
