# Day 7 — containerize the API so it runs with one command instead of
# manual venv/pip/Postgres-password setup.
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (separate layer) so Docker can cache this
# step and skip re-downloading packages every time only the code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the actual project code.
COPY crawler/ ./crawler/
COPY indexer/ ./indexer/
COPY ranking/ ./ranking/
COPY api/ ./api/

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]