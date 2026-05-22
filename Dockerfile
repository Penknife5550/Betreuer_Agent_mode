FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies for WeasyPrint and general build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    libglib2.0-0 \
    shared-mime-info \
    fonts-liberation \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download Tailwind CLI (standalone, kein Node erforderlich) fuer CSS-Build.
# TAILWIND_VERSION kann ueber Build-Arg ueberschrieben werden.
ARG TAILWIND_VERSION=v3.4.13
ARG TARGETARCH=x64
RUN curl -fsSL -o /usr/local/bin/tailwindcss \
    "https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/tailwindcss-linux-${TARGETARCH}" \
    && chmod +x /usr/local/bin/tailwindcss

# Non-root-User fuer die App. UID 1000 damit gemountete Volumes
# auf gaengigen Linux-Hosts nicht root-owned sind.
RUN groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --create-home --shell /sbin/nologin app

# Set working directory
WORKDIR /app

# Install Python dependencies first (besserer Docker-Cache)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (spaeter als deps, um Cache besser zu nutzen)
COPY . /app/

# Ensure staticfiles + media dirs exist and belong to the non-root user
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app

# Tailwind-CSS bauen (ersetzt das bisherige CDN-Einbinden im Template).
# Fail-fast: gescheiterter Tailwind-Build muss den Image-Build stoppen,
# sonst landet eine stale CSS im Container -- UI-Aenderungen wie Schatten
# oder Ring-Utilities wuerden dann stillschweigend nicht greifen.
RUN tailwindcss \
    -c /app/tailwind.config.js \
    -i /app/static/css/tailwind.input.css \
    -o /app/static/css/tailwind.css \
    --minify

# Collect static files mit production-Settings, damit das ManifestStaticFiles-
# Storage zur Build-Zeit das staticfiles.json-Manifest erzeugt. Sonst wirft
# Django zur Laufzeit "Missing staticfiles manifest entry" beim ersten Render.
# Dummy-ENVs erfuellen die Fail-Fast-Checks in production.py; werden zur
# Laufzeit durch die echte .env ueberschrieben.
USER app
RUN DATABASE_URL=sqlite:///tmp/build.db \
    SECRET_KEY=build-time-only-not-for-runtime-xxxxxxxxxxxxxxxxxxxxxxxx \
    ALLOWED_HOSTS=build.example.com \
    FERNET_KEY=build-time-placeholder \
    DJANGO_SETTINGS_MODULE=betreuer_project.settings.production \
    python manage.py collectstatic --noinput

# Healthcheck wird in docker-compose.yml definiert (war hier doppelt).

EXPOSE 8000

# Run with Waitress WSGI server. Threads & Connections bewusst gesetzt,
# damit gelegentliche PDF-/n8n-Wartezeiten nicht alle Worker blocken.
CMD ["waitress-serve", \
     "--port=8000", \
     "--host=0.0.0.0", \
     "--threads=8", \
     "--connection-limit=200", \
     "--channel-timeout=120", \
     "betreuer_project.wsgi:application"]
