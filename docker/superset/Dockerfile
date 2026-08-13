FROM apache/superset:6.0.0

USER root

COPY requirements.txt /tmp/superset-requirements.txt
COPY superset_config.py /app/pythonpath/superset_config.py

RUN . /app/.venv/bin/activate \
    && uv pip install \
        --no-cache \
        --requirement /tmp/superset-requirements.txt

USER superset