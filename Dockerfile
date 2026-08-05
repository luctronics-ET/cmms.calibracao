FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY frontend/ frontend/
COPY alembic/ alembic/
COPY alembic.ini entrypoint.sh ./
RUN chmod +x entrypoint.sh
# SISCALIB_DATA só usado em modo SQLite local
ENV SISCALIB_DATA=/tmp/siscalib
EXPOSE 8080
CMD ["./entrypoint.sh"]
