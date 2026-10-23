# Pinned to the patched release (Oct 2026 security fixes); bump deliberately.
FROM python:3.12.15-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# The app doesn't need root: run it as an unprivileged user.
RUN useradd --system --no-create-home appuser
USER appuser

# The hosting platform sets $PORT at runtime; 8080 is the usual default.
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
