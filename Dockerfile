# 🏗️ ESTÁGIO 1: BUILD
FROM python:3.11-slim AS builder

# Evita que o Python gere arquivos .pyc e permite logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do sistema necessárias para compilar pacotes Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia apenas o requirements para aproveitar o cache de camadas do Docker
COPY requirements.txt .

# Cria um virtualenv para isolar dependências
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir -r requirements.txt

# 🚀 ESTÁGIO 2: PRODUÇÃO
FROM python:3.11-slim

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Instala libpq (necessário para psycopg2 rodar) e limpa cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copia o virtualenv do estágio de build
COPY --from=builder /opt/venv /opt/venv

# Cria usuário não-root para segurança
RUN addgroup --system django && adduser --system --group django

# Copia o código do projeto
COPY . .

# Ajusta permissões
RUN chown -R django:django /app

# Muda para o usuário django
USER django

# Expõe a porta padrão do Django
EXPOSE 8000

# Comando para rodar a aplicação usando Gunicorn padrão (WSGI)
CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "--log-level", "debug"]
