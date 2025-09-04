AGENT_API_URL := http://localhost:8005/receive_alert

all: 
	docker-compose up --build -d
	@$(MAKE) links

stop: 
	docker-compose down

links:
	@echo "API : http://localhost:8080"
	@echo "Prometheus : http://localhost:9090"
	@echo "Grafana : http://localhost:3000"

api:
	docker-compose up -d --build api

test-api:
	curl -X 'POST' \
		'http://localhost:8080/predict' \
		-H 'accept: application/json' \
		-H 'Content-Type: application/json' \
		-d '{"text": "What a spectacular shot from Steph Curry!"}'

evaluation:
	docker-compose up -d --build evaluation

trigger-alert-critical:
	@echo "Triggering a CRITICAL alert to the AIOps Monitor Agent Service..."
	curl -X POST -H "Content-Type: application/json" -d '{"alerts": [{"labels": {"alertname": "HighCPULoad", "service": "news-classifier-api"},"annotations": {"summary": "CPU load is critical on news-classifier-api!"}}]}' $(AGENT_API_URL)
