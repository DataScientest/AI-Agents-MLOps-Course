FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY state.py .
COPY agent_nodes.py .
COPY config.py .
COPY agents/ ./agents/
COPY nodes/ ./nodes/
COPY tools/ ./tools/
COPY prompts/ ./prompts/
COPY knowledge_base/ ./knowledge_base/

COPY main.py .

EXPOSE 8005

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"]