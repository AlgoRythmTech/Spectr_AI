# Spectr Backend — Single image, both modes (multi-tenant SaaS + dedicated firm instances)
# Behavior controlled by FIRM_SHORT env var:
#   FIRM_SHORT=""     → runs as spectr.in (multi-tenant, per-user isolation)
#   FIRM_SHORT="cam"  → runs as cymllp.spectr.in (dedicated CAM instance)

FROM python:3.11-slim AS builder

# System deps for building (cached layer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY backend/requirements.txt .
RUN pip install --upgrade pip && pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# ---------- Runtime stage ----------
FROM python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/algorythm/spectr"
LABEL org.opencontainers.image.description="Spectr — AI Legal Intelligence for India"

# Runtime system deps (Chromium for sandbox-less browser fallback, wkhtmltopdf, fonts)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    wkhtmltopdf \
    fonts-liberation \
    fonts-dejavu \
    fonts-noto \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps from wheels
COPY --from=builder /build/wheels /wheels
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && rm -rf /wheels

# Copy application code
COPY backend/ /app/

# Copy firms directory (contains per-firm configs + default)
COPY firms/ /app/firms/

# Create runtime dirs
RUN mkdir -p /app/uploads /app/exports /app/logs

# Security: run as non-root
RUN useradd -m -u 1000 spectr && chown -R spectr:spectr /app
USER spectr

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Defaults (override at deploy time)
ENV FIRM_SHORT=""
ENV PORT=8000
ENV WORKERS=2
ENV LOG_LEVEL=info

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT} --workers ${WORKERS} --log-level ${LOG_LEVEL} --proxy-headers --forwarded-allow-ips='*'"]
