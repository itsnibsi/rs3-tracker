FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app.py collector.py config.py db.py log.py skills.py utils.py web.py ./
COPY services ./services
COPY routes ./routes
RUN uv pip install --system .

COPY static ./static
COPY templates ./templates

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]