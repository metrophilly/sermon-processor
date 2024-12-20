COMPOSE = docker-compose
SERVICE = sermon-processor
TEST_SERVICE = tests
LOG_DIR = tests/logs
TIMESTAMP = $(shell date +"%Y%m%d_%H%M%S")
LOG_FILE = $(LOG_DIR)/test_output_$(TIMESTAMP).log

.DEFAULT_GOAL := run

create-log-dir:
	@mkdir -p $(LOG_DIR)

# Build the Docker image for production
build:
	@echo "Building Docker images for production..."
	$(COMPOSE) build $(SERVICE)

# Stop and clean up
clean:
	@echo "Stopping all Docker services and cleaning up..."
	$(COMPOSE) down
	docker image prune -f || true
	@echo "Cleanup complete."

# Run the production service (depends on build and clean)
run: clean build
	@echo "Running '$(SERVICE)' Docker service..."
	$(COMPOSE) run --rm --name $(SERVICE) $(SERVICE)
	@echo ""
	@echo "---"
	@echo "Production environment is running."

# Run tests
test: create-log-dir
	@echo "Building Docker images for testing..."
	$(COMPOSE) build $(TEST_SERVICE)
	@echo "Running tests..."
	$(COMPOSE) run --rm $(TEST_SERVICE) | tee $(LOG_FILE)
	@echo "Test logs saved to $(LOG_FILE)"
	@echo ""
	@echo "---"
	@echo "Cleaning up dangling Docker images..."
	docker image prune -f || true