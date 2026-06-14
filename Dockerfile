FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY frontend/ frontend/
COPY alembic/ alembic/
COPY alembic.ini entrypoint.sh ./
RUN chmod +x entrypoint.sh
ENV SISCALIB_DATA=/data
VOLUME ["/data"]
EXPOSE 8080
CMD ["./entrypoint.sh"]
