FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Player saves should live on a mounted volume so they survive container
# restarts/redeploys. Ground items, mob HP, etc. are in-memory only and are
# NOT persisted -- that's expected (see README "Persistence & limitations").
VOLUME ["/app/players"]

EXPOSE 8000

# Single worker, single process: the engine keeps all live game state
# (connected players, mob instances, dropped items) in process memory, so
# this app cannot be scaled to multiple workers/containers. Run exactly one.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
