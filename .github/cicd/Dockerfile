FROM python:3.12-slim
ARG VCS_REF=local
LABEL org.opencontainers.image.source="https://github.com/Samucau1/edufast-2.0" \
      org.opencontainers.image.revision=$VCS_REF
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY api/requirements.txt /tmp/app-requirements.txt
COPY .github/cicd/requirements.txt /tmp/server-requirements.txt
RUN pip install --no-cache-dir -r /tmp/app-requirements.txt -r /tmp/server-requirements.txt \
    && useradd --uid 10001 --create-home edufast
COPY --chown=edufast:edufast api/ /app/
RUN mkdir -p /app/uploads && chown edufast:edufast /app/uploads
USER edufast
EXPOSE 8000
# Um worker evita inicializações concorrentes do esquema legado.
CMD ["gunicorn", "--bind=0.0.0.0:8000", "--workers=1", "--threads=4", "--timeout=60", "--access-logfile=-", "--error-logfile=-", "app:create_app()"]
