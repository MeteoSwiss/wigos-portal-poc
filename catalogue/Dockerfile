FROM python:3.13-slim

WORKDIR /app

COPY catalogue/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY catalogue/pygeoapi-config.yml /app/catalogue/pygeoapi-config.yml
COPY catalogue/docker-entrypoint.sh /app/catalogue/docker-entrypoint.sh
COPY scripts /app/scripts
COPY data /app/data
RUN chmod +x /app/catalogue/docker-entrypoint.sh /app/scripts/*.py && mkdir -p /app/data/wmdr2 /app/data/records

ENV PYGEOAPI_CONFIG=/app/catalogue/pygeoapi-config.yml
ENV PYGEOAPI_OPENAPI=/app/catalogue/openapi.yml
ENV WIGOS_CATALOGUE_DB=/app/data/wigos-facilities.tinydb
ENV WMDR2_SYNC_ON_START=1

EXPOSE 10000
ENTRYPOINT ["/app/catalogue/docker-entrypoint.sh"]
