FROM node:22-alpine AS frontend-build
WORKDIR /work
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/srv/dac/backend:/srv/dac
WORKDIR /srv/dac
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements.lock && useradd --create-home --uid 10001 dac
COPY . .
COPY --from=frontend-build /work/dist ./frontend/dist
USER dac
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
