FROM python:3.12-slim

WORKDIR /app

# Dependências de sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar pyproject.toml e instalar deps
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# Copiar código-fonte
COPY src/ src/
COPY data/ data/

# Cria diretório de dados
RUN mkdir -p data/raw

ENTRYPOINT ["python", "-m", "careercompass"]
