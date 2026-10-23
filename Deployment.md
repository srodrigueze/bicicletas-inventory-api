# Despliegue a GCP (Cloud Run)

Infraestructura ya existente (ver DEV-007 en la bóveda): proyecto `jac-bicicletas`,
buckets de Cloud Storage `jac-bicicletas-{dev,test,prod}`, y la cuenta de servicio
`bicicletas-api-prod@jac-bicicletas.iam.gserviceaccount.com` con permisos solo sobre el
bucket `prod`. El despliegue usa el `Dockerfile` de la raíz del repo (sin buildpacks).

## Variables de entorno en producción

| Variable | Obligatoria | Notas |
|---|---|---|
| `DATABASE_URL`, `DATABASE_URL_DIRECT` | Sí | Cadenas de la rama `prod` de Neon (pooler / directa). Van en Secret Manager. |
| `JWT_SECRET_KEY` | Sí | Propio de producción, nunca el de `dev`/`test`. Va en Secret Manager. |
| `GCS_BUCKET_NAME`, `IMAGE_BASE_URL` | Sí | Bucket `prod` y su URL pública. |
| `STORAGE_BACKEND` | No | `gcs` por defecto. |
| `ENABLE_API_DOCS` | **No definir** | Swagger queda deshabilitado por defecto; no lo actives en producción. |
| `LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCK_MINUTES` | No | 5 intentos / 15 minutos por defecto. |

## 1. Crear la rama `prod` en Neon

Desde la consola de Neon (no es un recurso de GCP): crea una rama nueva llamada `prod` en
el mismo proyecto, independiente de `dev`/`test`. Copia sus dos cadenas de conexión
(pooler y directa).

## 2. Generar un `JWT_SECRET_KEY` propio para producción

Nunca reutilices el de `dev`/`test`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## 3. Guardar los secretos en Secret Manager

```bash
gcloud services enable secretmanager.googleapis.com --project=jac-bicicletas

echo -n "<DATABASE_URL de prod>" | gcloud secrets create database-url-prod --data-file=- --project=jac-bicicletas
echo -n "<DATABASE_URL_DIRECT de prod>" | gcloud secrets create database-url-direct-prod --data-file=- --project=jac-bicicletas
echo -n "<JWT_SECRET_KEY generado en el paso 2>" | gcloud secrets create jwt-secret-key-prod --data-file=- --project=jac-bicicletas
```

Dale acceso de lectura a la cuenta de servicio que usará Cloud Run:
```bash
for secret in database-url-prod database-url-direct-prod jwt-secret-key-prod; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:bicicletas-api-prod@jac-bicicletas.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=jac-bicicletas
done
```

## 4. Aplicar las migraciones contra `prod` (una sola vez, antes del primer despliegue)

Desde tu máquina, con un `.env` apuntando temporalmente a las cadenas de conexión de
`prod` (no las subas a ningún repo):
```bash
alembic upgrade head
```

## 5. Crear el superadministrador semilla en `prod`

Con el mismo `.env` temporal apuntando a `prod`:
```bash
python -m scripts.create_admin "Nombre Completo" <documento>
```

## 6. Desplegar

```bash
gcloud run deploy bicicletas-inventory-api \
  --source . \
  --project=jac-bicicletas \
  --region=us-central1 \
  --service-account=bicicletas-api-prod@jac-bicicletas.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --set-secrets="DATABASE_URL=database-url-prod:latest,DATABASE_URL_DIRECT=database-url-direct-prod:latest,JWT_SECRET_KEY=jwt-secret-key-prod:latest" \
  --set-env-vars="GCS_BUCKET_NAME=jac-bicicletas-prod,IMAGE_BASE_URL=https://storage.googleapis.com/jac-bicicletas-prod/"
```

`--allow-unauthenticated` es correcto aquí: Cloud Run queda abierto a internet, pero cada
endpoint de la API sigue exigiendo su propio JWT (excepto `GET /`, el health check). Cloud
Run construye la imagen con el `Dockerfile`, la sube a Artifact Registry y devuelve una URL
pública (`https://bicicletas-inventory-api-xxxxx-uc.a.run.app`).

## 7. Verificar

```bash
curl https://<url-del-servicio>/
# {"status": "ok"}
curl -o /dev/null -w "%{http_code}\n" https://<url-del-servicio>/docs
# 404 (el Swagger no debe estar expuesto en producción)
```

Si da `503`, la base de datos no respondió — revisa que el secreto `DATABASE_URL` sea el
correcto y que la rama `prod` de Neon esté activa.

## Despliegues posteriores

Cada vez que haya una migración nueva (columna, tabla, enum), repite el paso 4 contra
`prod` **antes** de re-desplegar el código que depende de ese cambio — Cloud Run no
corre migraciones automáticamente. Para el código en sí, basta con repetir el paso 6: crea
una revisión nueva y la cambia de tráfico automáticamente.

### Migraciones que afectan a los usuarios existentes

Las migraciones `b7e4d2a91c5f` y `c4f1a8e63d27` agregan los campos de control de acceso
(`must_change_password`, `failed_login_attempts`, `locked_until`, `token_version`).
Al aplicarlas, **todos los usuarios existentes quedan obligados a cambiar su contraseña en
su próximo ingreso**. Avísale a los administradores antes de desplegar.
