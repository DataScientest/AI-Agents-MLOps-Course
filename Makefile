AGENT_API_URL := http://localhost:8005/diagnose_alert

all: 
	docker compose up --build -d
	@$(MAKE) links

stop: 
	docker compose down

links:
	@echo "API : http://localhost:8081"
	@echo "Prometheus : http://localhost:9091"
	@echo "Grafana : http://localhost:3001"

api:
	docker compose up -d --build api

test-api:
	curl -X 'POST' \
		'http://localhost:8081/predict' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-d '{"text": "What a spectacular shot from Steph Curry!"}'

evaluation:
	docker compose up -d --build evaluation

trigger-alert-critical:
	@echo "Triggering a CRITICAL alert to the AIOps Monitor Agent Service..."
	curl -X POST -H "Content-Type: application/json" -d '{"alerts": [{"labels": {"alertname": "HighCPULoad", "service": "", "severity": "critical"}, "annotations": {"summary": "CPU load is unusually high.", "description": "Observed sustained high CPU utilization, exceeding 90% for 10 minutes."}}]}' http://localhost:8005/diagnose_alert            

# Offline tests (fake LLM, no API key, no Docker): same pinned deps as the Agent Core image
test-offline:
	cd tests/offline && uv run --no-project --python 3.12 \
		--with-requirements ../../src/aiops_agent_monitor/requirements.txt \
		--with pytest==9.1.1 pytest -v
