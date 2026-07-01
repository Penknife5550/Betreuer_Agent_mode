#!/bin/sh
set -e

# ---------------------------------------------------------------------------
# Container-Entrypoint
# ---------------------------------------------------------------------------
# Sammelt beim Start die Static-Dateien ein, damit das
# ManifestStaticFiles-Manifest (staticfiles.json) im gemounteten Volume
# IMMER zum aktuellen Image passt.
#
# Hintergrund: /app/staticfiles ist ein persistentes Named-Volume. Wird ein
# neues Image mit zusaetzlichen/geaenderten Static-Dateien deployt, ueberdeckt
# der ALTE Volume-Inhalt beim Mount das im Build erzeugte Manifest. WhiteNoise
# liest dann ein veraltetes staticfiles.json -> beim ersten {% static %}-Lookup
# einer neuen Datei wirft Django "Missing staticfiles manifest entry" -> HTTP
# 500 auf JEDER Seite. collectstatic beim Start haelt das Manifest aktuell.
#
# WICHTIG: Wir erzwingen dieselbe Settings-Aufloesung wie der Laufzeit-Server.
# wsgi.py faellt auf production zurueck (Manifest-Storage), manage.py wuerde
# sonst auf development defaulten (Storage OHNE Manifest) -> collectstatic
# wuerde das falsche Storage befuellen und den 500 NICHT beheben.
if [ "${RUN_COLLECTSTATIC:-0}" = "1" ]; then
    echo "[entrypoint] collectstatic (settings: ${DJANGO_SETTINGS_MODULE:-betreuer_project.settings.production}) ..."
    python manage.py collectstatic --noinput \
        --settings="${DJANGO_SETTINGS_MODULE:-betreuer_project.settings.production}"
fi

exec "$@"
