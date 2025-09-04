all: 
	docker-compose up --build -d
	@$(MAKE) links

stop: 
	docker-compose down

links:
	@echo "API : http://localhost:8080"
	@echo "Prometheus : http://localhost:9090"
	@echo "Grafana : http://localhost:3000"
	@echo "Loki : http://localhost:3100"

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
