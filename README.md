# Sistema de préstamo de bicicletas

Proyecto comunitario de código abierto para gestionar el inventario de bicicletas y sus
préstamos en Medellín. Permite administrar el estado de las bicicletas (condición física,
disponibilidad) y ofrece una API para que la comunidad registre el préstamo de una o
varias bicis durante el día, sin costo de uso ni de infraestructura.

## Stack

- **Backend**: FastAPI (Python 3.12) + SQLModel (ORM) + Alembic (migraciones)
- **Base de datos**: PostgreSQL en [Neon](https://neon.tech) (tier gratuito)
- **Frontend**: Next.js / React (pendiente), desplegado en Vercel
- **Hosting backend**: Google Cloud Run (contenedor, escala a cero) — pendiente

## Arquitectura

El backend sigue una **arquitectura en capas inspirada en Clean/Hexagonal Architecture**,
con **Repository Pattern** para invertir la dependencia hacia la base de datos. No es "la"
forma oficial de estructurar un proyecto FastAPI (el framework no impone ninguna), es la
decisión tomada en este proyecto para mantener la lógica de negocio testeable y
desacoplada del ORM concreto.

```
Cliente (Next.js)
      ↓
Routers (app/api/routers)       — reciben HTTP, delegan al service, no contienen lógica de negocio
      ↓
Services (app/services)          — lógica de negocio (ej: no prestar una bici en mal estado
                                    o ya prestada)
      ↓
Repositories — interfaz (app/domain/repositories)  — contrato abstracto (ABC) de acceso a datos
      ↓
Repositories — implementación (app/infrastructure/repositories)  — SQLModel + Postgres
```

Los `services` dependen de la interfaz abstracta del repositorio (`domain/repositories/*`),
nunca de la implementación SQL concreta (**Dependency Inversion**, principio SOLID). FastAPI
inyecta la implementación real vía `Depends()` (ver `app/api/deps.py`). Esto permite testear
services con un repositorio falso/mock sin tocar la base de datos, y cambiar de motor de
persistencia sin reescribir la lógica de negocio.

### Estructura del proyecto

```
.
├── app/
│   ├── main.py                    # instancia FastAPI, registra los routers
│   ├── core/
│   │   ├── config.py               # Settings (variables de entorno)
│   │   └── database.py             # engine de SQLModel + dependencia get_session()
│   ├── domain/
│   │   ├── entities/                # modelos SQLModel (tablas): bicycle, loan, user
│   │   └── repositories/            # interfaces abstractas (ABC) de los repositorios
│   ├── infrastructure/
│   │   └── repositories/            # implementación concreta de los repositorios (SQLModel)
│   ├── schemas/                     # DTOs Pydantic (entrada/salida de la API)
│   ├── services/                    # lógica de negocio
│   └── api/
│       ├── deps.py                   # inyección de dependencias (session → repo → service)
│       └── routers/                  # controllers de FastAPI
├── migrations/                       # migraciones de Alembic
├── requirements.txt
└── README.md
```

### Modelo de dominio

- **Bicycle**: `code`, `condition` (`good`/`bad`, condición física), `size`
  (`small`/`medium`/`large`), `observations`, `photo_url`. La disponibilidad **no se
  guarda** como columna: se calcula en `BicycleService` a partir de `condition == good`
  y de que no tenga un `Loan` activo.
- **Loan**: registra el préstamo de una o varias bicicletas a la vez (relación
  muchos-a-muchos vía `LoanBicycleLink`) — `requester_name`, `id_document`, `phone`,
  `loan_datetime`, `return_datetime` (nulo hasta que se devuelve), `status`
  (`in_progress`/`finished`).
- **User**: usuarios del sistema — `full_name`, `document` (número de documento de
  identidad, único, usuario de acceso), `hashed_password` (bcrypt), `role`
  (`administrador`/`operador`), `status` (`activo`/`inactivo`), `is_superadmin`
  (booleano, solo aplicable a `administrador`, único en el sistema, inmutable). Ver
  reglas completas en la bóveda de documentación,
  `Requisitos/REQ-001 - Autenticacion y gestion de usuarios.md`.

## Autenticación

`POST /auth/login` recibe `document`/`password`. La contraseña inicial de todo usuario
es derivada (últimos 4 dígitos del documento); un usuario puede cambiarla después vía
`POST /users/me/change-password`. Login valida contra el hash guardado (`bcrypt`),
rechaza usuarios `inactivo` con el mismo mensaje genérico que credenciales inválidas, y
devuelve un JWT (`pyjwt`, `HS256`, expira en `JWT_EXPIRE_MINUTES` — 6h por defecto,
RNG-07). Requiere `JWT_SECRET_KEY` en `.env` (generar con
`python -c "import secrets; print(secrets.token_hex(32))"`, nunca commitear).

No hay auto-registro a propósito (RNG-08). Solo existe un único punto de entrada sin
autenticación previa: `scripts/create_admin.py`, que crea **exclusivamente** al
superadministrador semilla (se niega a correr si ya existe uno):

```bash
python -m scripts.create_admin "Nombre Completo" <documento>
```

Cualquier otro usuario (administrador u operador) se crea vía `POST /users/`, protegido
por JWT y restringido a usuarios con rol `administrador` — ver
`app/api/routers/users.py` y `app/api/deps.py` (`get_current_user`,
`require_administrador`).

Todos los endpoints de `bicycles`, `loans`, `clients`, `audits` y `reports` requieren
JWT (`CurrentUserDep`/`AdminUserDep` en `app/api/deps.py`); el único endpoint público
sin autenticación es el health check (`GET /`, ver abajo).

## Health check

`GET /` no requiere autenticación y confirma dos cosas: que el proceso está arriba y
que la conexión a la base de datos responde (`SELECT 1`). Devuelve `200
{"status": "ok"}` si todo está bien, o `503` si la base de datos no responde. Pensado
para monitores de uptime externos y para el health check/liveness probe de Cloud Run.

## Configuración local

1. Clona el repositorio y entra a la carpeta del proyecto.
2. Crea y activa un entorno virtual:
   ```bash
   python3.12 -m venv env
   source env/bin/activate
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Crea un archivo `.env` en la raíz (no se sube al repo, está en `.gitignore`) con
   **dos** cadenas de conexión a tu rama de desarrollo en Neon — la app usa la de
   pooler en runtime, Alembic usa la directa:
   ```
   DATABASE_URL=postgresql+psycopg://usuario:password@ep-xxxx-pooler.<region>.aws.neon.tech/dbname?sslmode=require
   DATABASE_URL_DIRECT=postgresql+psycopg://usuario:password@ep-xxxx.<region>.aws.neon.tech/dbname?sslmode=require
   ```
5. Levanta el servidor local:
   ```bash
   uvicorn app.main:app --reload
   ```
6. Prueba la API (Swagger UI, incluido con FastAPI) en `http://localhost:8000/docs`.

## Migraciones de base de datos

Cada vez que cambies una entity en `app/domain/entities/`:

```bash
alembic revision --autogenerate -m "descripción del cambio"
alembic upgrade head
```

Revisa siempre el archivo de migración generado en `migrations/versions/` antes de
aplicarlo — el autogenerate de Alembic con SQLModel a veces omite el `import sqlmodel`
que sus propios tipos de columna necesitan, y no siempre emite el `CREATE TYPE`/
`DROP TYPE` de los enums nativos de Postgres (revísalo también).

## Pruebas automatizadas

La suite corre contra una rama **dedicada de Neon llamada `test`** — nunca contra
`dev` ni producción. Antes de correrla, crea un archivo `.env.test` en la raíz (no se
sube al repo) con las cadenas de conexión de esa rama:

```
DATABASE_URL=postgresql+psycopg://usuario:password@ep-xxxx-pooler.<region>.aws.neon.tech/dbname?sslmode=require
DATABASE_URL_DIRECT=postgresql+psycopg://usuario:password@ep-xxxx.<region>.aws.neon.tech/dbname?sslmode=require
JWT_SECRET_KEY=cualquier-valor-de-prueba
```

```bash
pip install -r requirements.txt   # incluye pytest y httpx
pytest
```

`tests/conftest.py` aplica `alembic upgrade head` sobre la rama `test` al inicio de
la corrida y trunca todas las tablas después de cada test — cada test parte de una
base de datos limpia, sin depender del orden de ejecución. Los tests hablan con la
API real vía `fastapi.testclient.TestClient` (login real, JWT real), no con mocks.

Cada requisito nuevo que se implemente (ver la bóveda de Obsidian del proyecto,
carpeta `Desarrollo/`) debe agregar su propio archivo `tests/test_<módulo>.py`, para
que la suite completa sirva como regresión antes de cada despliegue.

## Despliegue a GCP (Cloud Run)

Pendiente: falta el `Dockerfile` y la configuración de Secret Manager para las variables
de entorno de producción.

> **Importante**: antes de desplegar, fija las versiones exactas de las dependencias que
> ya probaste localmente. Esto evita que el build en la nube instale versiones distintas
> a las que usaste en desarrollo:
> ```bash
> pip freeze > requirements.txt
> ```

Con eso listo, el despliegue se hará con:

```bash
gcloud run deploy --source .
```

Cloud Run construye la imagen a partir del `Dockerfile`, la sube a Artifact Registry y
despliega el servicio, devolviendo una URL pública.

Las variables de entorno de producción (`DATABASE_URL`, `DATABASE_URL_DIRECT` apuntando a
la rama de producción en Neon) se configurarán como secretos en Secret Manager, no en el
código.

## Contribuir

Este es un proyecto comunitario y abierto a contribuciones. Si quieres ayudar, abre un
issue o un pull request.
