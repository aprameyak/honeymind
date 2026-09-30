FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir httpx==0.28.1
COPY actors /app/actors
COPY scripts /app/scripts
ENV PYTHONUNBUFFERED=1
# Hard allowlist enforced in code — never connect outside lab services.
CMD ["python", "-m", "actors.run_all"]
