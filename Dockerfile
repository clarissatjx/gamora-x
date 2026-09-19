# Builds the React frontend, then a Python image that serves both the built frontend and the
# FastAPI backend from one process (webapp/backend/main.py's SPA-fallback route) — one Cloud Run
# service, no CORS between separately hosted frontend/backend. See webapp/README.md.

FROM node:20-slim AS frontend-build
WORKDIR /src/webapp/frontend
COPY webapp/frontend/package.json webapp/frontend/package-lock.json ./
RUN npm ci
COPY webapp/frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

# scikit-learn/scipy/numpy have manylinux wheels for this Python/arch in the pinned ranges, but
# build-essential is kept as a fallback so a missing wheel doesn't break the build.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
COPY webapp/backend/requirements.txt ./webapp/backend/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r webapp/backend/requirements.txt

COPY app ./app
COPY subsystems ./subsystems
COPY webapp/backend ./webapp/backend
COPY --from=frontend-build /src/webapp/frontend/dist ./webapp/frontend/dist

# Cloud Run injects $PORT (defaults to 8080 locally too); shell form so it expands.
ENV PORT=8080
EXPOSE 8080
CMD exec uvicorn webapp.backend.main:app --host 0.0.0.0 --port ${PORT}
