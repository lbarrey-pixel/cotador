FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
COPY db ./db
RUN pip install --no-cache-dir -e .
EXPOSE 8000
CMD ["uvicorn", "app.main:criar_app_do_ambiente", "--factory", "--host", "0.0.0.0", "--port", "8000"]
