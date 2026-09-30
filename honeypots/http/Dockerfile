FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.6 uvicorn==0.34.0 httpx==0.28.1 pydantic==2.10.3
COPY app.py .
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
USER nobody
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
