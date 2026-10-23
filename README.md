# Sistema de préstamo de bicicletas

Proyecto comunitario de código abierto para gestionar el inventario de bicicletas y sus
préstamos en Medellín. Permite administrar el estado de las bicicletas (condición física,
disponibilidad) y ofrece una API para que la comunidad registre el préstamo de una o
varias bicis durante el día, sin costo de uso ni de infraestructura.

## Stack

- **Backend**: FastAPI (Python 3.12) + SQLModel (ORM) + Alembic (migraciones)
- **Base de datos**: PostgreSQL en [Neon](https://neon.tech) (tier gratuito)
- **Frontend**: Next.js / React (pendiente), desplegado en Vercel
- **Hosting backend**: contenedor Docker (ver [Deployment.md](Deployment.md)) — pendiente

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

`POST /auth/login` recibe `document`/`password`. Valida contra el hash guardado (`bcrypt`),
rechaza usuarios `inactivo` con el mismo mensaje genérico que credenciales inválidas, y
devuelve un JWT (`pyjwt`, `HS256`, expira en `JWT_EXPIRE_MINUTES` — 6h por defecto,
RNG-07). Requiere `JWT_SECRET_KEY` en `.env` (generar con
`python -c "import secrets; print(secrets.token_hex(32))"`, nunca commitear).

Cada administrador le comunica al usuario nuevo cómo ingresar por primera vez. Toda cuenta
nueva (o reseteada con `POST /users/{id}/reset-password`) queda con
`must_change_password: true` y no puede usar ningún endpoint —responden `403 Password
change required`— salvo `POST /users/me/change-password` y `GET /users/me`. El flag viene
en la respuesta del login para que el frontend redirija al cambio de contraseña.

**Revocación de tokens:** cambiar o resetear una contraseña invalida todos los tokens
emitidos antes (campo `token_version`), así que tras `change-password` hay que volver a
iniciar sesión. Ambas acciones quedan en la auditoría (`password_change`,
`password_reset`). Las contraseñas admiten hasta 72 bytes (límite de bcrypt).

**Bloqueo por intentos fallidos:** tras `LOGIN_MAX_ATTEMPTS` (5) intentos fallidos
consecutivos la cuenta rechaza el login con `429` y cabecera `Retry-After` durante
`LOGIN_LOCK_MINUTES` (15), incluso con la contraseña correcta. Un login exitoso reinicia
el contador, y `POST /users/{id}/reset-password` también desbloquea la cuenta. El conteo
es atómico en la base de datos, así que peticiones paralelas no lo evaden. Esto protege
cada cuenta, no la IP: para frenar un barrido entre muchas cuentas conviene además un
límite en el borde (WAF del proveedor).

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
sin autenticación es el health check (`GET /`, ver abajo). Todas las respuestas llevan
cabeceras de seguridad (`nosniff`, `X-Frame-Options`, `HSTS`, `no-store`).

## Documentación de la API (Swagger)

`/docs`, `/redoc` y `/openapi.json` están **deshabilitados por defecto** (RNG-01). Para
desarrollo local agrega `ENABLE_API_DOCS=true` a tu `.env`; en producción no definas esa
variable.

## Almacenamiento de imágenes

Las fotos de las bicicletas se guardan detrás de la interfaz `ImageStorageRepository`
(`app/domain/repositories/image_storage_repository.py`). El proveedor se elige con
`STORAGE_BACKEND` (por ahora solo `gcs`). Para soportar otro proveedor, implementa esa
interfaz en `app/infrastructure/repositories/` y agrega su rama en
`get_image_storage_repository()` (`app/api/deps.py`). Solo se aceptan JPEG, PNG y WebP de
hasta 5 MB; el formato se verifica por el contenido del archivo, no por lo que declare el
cliente.

## Health check

`GET /` no requiere autenticación y confirma dos cosas: que el proceso está arriba y
que la conexión a la base de datos responde (`SELECT 1`). Devuelve `200
{"status": "ok"}` si todo está bien, o `503` si la base de datos no responde. Pensado
para monitores de uptime externos y para el health check/liveness probe de la plataforma de hosting.

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
   JWT_SECRET_KEY=<ver sección Autenticación>
   ENABLE_API_DOCS=true
   ```
5. Levanta el servidor local:
   ```bash
   uvicorn app.main:app --reload
   ```
6. Prueba la API (Swagger UI, requiere `ENABLE_API_DOCS=true`) en `http://localhost:8000/docs`.

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

## Despliegue

Los pasos de despliegue (infraestructura, secretos, migraciones en producción) están en
[Deployment.md](Deployment.md).

## Contribuir

Este es un proyecto comunitario y abierto a contribuciones. Si quieres ayudar, abre un
issue o un pull request.
