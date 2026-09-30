FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home agent && mkdir /data && chown agent /data
USER agent
CMD ["uvicorn", "prediction_agent.api:app", "--host", "0.0.0.0", "--port", "8000"]
