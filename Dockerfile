FROM python:3.12-slim AS base

WORKDIR /app

# Dependências de sistema (só o necessário para compilar wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# --- Stage: instalação de dependências ---
FROM base AS deps

COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

# --- Stage: produção (sem dev deps) ---
FROM base AS production

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY src/ src/

# Diretórios de dados (volume em runtime)
RUN mkdir -p data/raw reports

ENTRYPOINT ["python", "-m", "careercompass"]
