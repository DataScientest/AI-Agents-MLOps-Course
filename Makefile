AGENT_GATEWAY_URL := http://localhost:8000/diagnose_alert

all: 
	docker compose up --build -d
	@$(MAKE) links

stop: 
	docker compose down

links:
	@echo "--- Service Links ---"
	@echo "API Gateway (Entrypoint): http://localhost:8000"
	@echo "Agent Core             : http://localhost:8005"
	@echo "Prometheus             : http://localhost:9090"
	@echo "Grafana                : http://localhost:3000"
	@echo "Loki                   : http://localhost:3100"
	@echo "----------------------"

api:
	docker compose up -d --build api

test-api:
	curl -X 'POST' \
		'http://localhost:8080/predict' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-d '{"text": "What a spectacular shot from Steph Curry!"}'

evaluation:
	docker compose up -d --build evaluation

# Chapter 5: Microservices Diagnosis
diagnose:
	@echo "🚀 Triggering diagnostic request via API Gateway (:8000)..." >&2
	@curl -s -X POST $(AGENT_GATEWAY_URL) \
		-H "Content-Type: application/json" \
		-d '{"alerts": [{"labels": {"alertname": "HighCPULoad", "service": "news-classifier-api", "severity": "critical"}, "annotations": {"summary": "CPU load is unusually high.", "description": "Observed sustained high CPU utilization, exceeding 90% for 10 minutes."}}]}' | jq .

# Watch the interactions between microservices
logs:
	docker compose logs -f api-gateway aiops-agent-monitor prometheus-tool-service loki-tool-service knowledge-base-service

status:
	@echo "Checking health of the microservices mesh..."
	@curl -s http://localhost:8000/health/mesh | jq '. | to_entries[] | {service: .key, status: .value}'
