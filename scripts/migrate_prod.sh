#!/usr/bin/env bash
# Applies Alembic migrations to the production database (Neon branch `prod`).
#
# Connection strings are read from `.env.prod` (git/docker-ignored), never from
# `.env`, so a dev shell can't hit prod by accident and vice versa.
#
# Usage:
#     scripts/migrate_prod.sh            # shows current revision, asks, upgrades
#     scripts/migrate_prod.sh --sql      # only prints the SQL, changes nothing
#
# `.env.prod` needs DATABASE_URL and DATABASE_URL_DIRECT (see Deployment.md);
# Alembic uses the direct one.

set -euo pipefail

cd "$(dirname "$0")/.."

PROD_ENV=".env.prod"
BIN="env/bin"

if [[ ! -f "$PROD_ENV" ]]; then
  echo "Falta $PROD_ENV con DATABASE_URL y DATABASE_URL_DIRECT de la rama prod." >&2
  exit 1
fi

# python-dotenv parses the file (the Neon URLs contain & and ?, which `source`
# would mangle) and injects it into the child process only.
run() { "$BIN/dotenv" -f "$PROD_ENV" run -- "$@"; }

target="$(run "$BIN/python" -c '
import os, sys
from urllib.parse import urlparse
url = os.environ.get("DATABASE_URL_DIRECT")
if not url:
    sys.exit("DATABASE_URL_DIRECT no está definida en .env.prod")
u = urlparse(url)
print(f"{u.hostname}{u.path}")
')"

# Guard: .env.prod must not point at the same database as dev or test.
for other in .env .env.test; do
  [[ -f "$other" ]] || continue
  other_target="$("$BIN/dotenv" -f "$other" run -- "$BIN/python" -c '
import os
from urllib.parse import urlparse
u = urlparse(os.environ.get("DATABASE_URL_DIRECT", ""))
print(f"{u.hostname}{u.path}")
')"
  if [[ "$other_target" == "$target" ]]; then
    echo "Abortado: $PROD_ENV apunta a la misma base que $other ($target)." >&2
    exit 1
  fi
done

if [[ "${1:-}" == "--sql" ]]; then
  run "$BIN/alembic" upgrade head --sql
  exit 0
fi

echo "Base de datos destino: $target"
echo
echo "Revisión actual:"
run "$BIN/alembic" current
echo
echo "Revisión objetivo:"
"$BIN/alembic" heads
echo

read -r -p "Escribe 'prod' para aplicar las migraciones a esta base: " answer
if [[ "$answer" != "prod" ]]; then
  echo "Cancelado."
  exit 1
fi

run "$BIN/alembic" upgrade head
echo
echo "Revisión final:"
run "$BIN/alembic" current
