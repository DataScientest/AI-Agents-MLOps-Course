AGENT_API_URL := http://localhost:8005/diagnose_alert
API_PORT := 8081
PROMETHEUS_PORT := 9091
GRAFANA_PORT := 3001


all: 
	docker compose up --build --force-recreate -d
	@$(MAKE) links

stop: 
	docker compose down

links:
	@echo "API : http://localhost:${API_PORT}"
	@echo "Prometheus : http://localhost:${PROMETHEUS_PORT}"
	@echo "Grafana : http://localhost:${GRAFANA_PORT}"

api:
	docker compose up -d --build api

test-api:
	curl -X 'POST' \
		'http://localhost:${API_PORT}/predict' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-d '{"text": "What a spectacular shot from Steph Curry!"}'

evaluation:
	docker compose up -d --build evaluation

trigger-alert-critical:
	@echo "Triggering a CRITICAL alert to the AIOps Monitor Agent Service..."
	curl -X POST \
		-H "Content-Type: application/json" \
		-d '{"alerts":[{"labels":{"alertname":"NewsClassifierHighCPULoad","service":"news-classifier-api","severity":"critical"},"annotations":{"summary":"CPU load is unusually high on news-classifier-api.","description":"Observed sustained high CPU utilization, exceeding 90% for 10 minutes."}}]}' \
		$(AGENT_API_URL)

show-agent-steps:
	@container_id=$$(docker compose ps -q aiops-agent-monitor); \
	if [ -z "$$container_id" ]; then \
		printf '{"error":"aiops-agent-monitor container not running"}\n'; exit 1; \
	fi; \
	container_name=$$(docker inspect --format '{{.Name}}' $$container_id | sed 's:^/::'); \
	docker logs $$container_id --since 10m --tail 400 | \
	python3 scripts/show_agent_steps.py "$$container_name"
