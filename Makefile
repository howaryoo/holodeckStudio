K8S := kubectl
PF := kubectl port-forward
CO := colima

COLIMA_CPUS ?= 4
COLIMA_MEM ?= 8
COLIMA_DISK ?= 60

.PHONY: start-cluster start stop delete status logs

start-cluster:
	$(CO) start --cpu $(COLIMA_CPUS) --memory $(COLIMA_MEM) --disk $(COLIMA_DISK) --kubernetes
	$(K8S) cluster-info

start: start-cluster
	$(K8S) apply -f k8s/config.yaml
	$(K8S) apply -f k8s/postgres.yaml
	$(K8S) apply -f k8s/minio.yaml
	$(K8S) wait --for=condition=ready pod -l app=holodeck,component=postgres --timeout=120s
	$(K8S) wait --for=condition=ready pod -l app=holodeck,component=minio --timeout=120s
	$(K8S) apply -f k8s/init-jobs.yaml
	$(K8S) wait --for=condition=complete job/holodeck-init-db --timeout=60s
	$(K8S) wait --for=condition=complete job/holodeck-init-bucket --timeout=60s
	@echo "--- Starting port-forwards ---"
	-nohup $(PF) svc/postgres 5432:5432 >/dev/null 2>&1 &
	-nohup $(PF) svc/minio 9000:9000 >/dev/null 2>&1 &
	-nohup $(PF) svc/minio 9001:9001 >/dev/null 2>&1 &
	@echo "--- Applying migrations ---"
	uv run alembic upgrade head

stop:
	-pkill -f "kubectl port-forward" 2>/dev/null || true
	$(K8S) delete -f k8s/init-jobs.yaml --ignore-not-found
	$(K8S) delete -f k8s/langfuse.yaml --ignore-not-found
	$(K8S) delete -f k8s/minio.yaml --ignore-not-found
	$(K8S) delete -f k8s/postgres.yaml --ignore-not-found
	$(K8S) delete -f k8s/config.yaml --ignore-not-found

delete: stop
	$(K8S) delete pvc postgres-data --ignore-not-found
	$(K8S) delete pvc minio-data --ignore-not-found

status:
	$(CO) status
	@echo "---"
	$(K8S) get pods -o wide
	@echo "---"
	$(K8S) get svc

logs:
	$(K8S) logs -l app=holodeck --all-containers --tail=50
