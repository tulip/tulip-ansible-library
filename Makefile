.PHONY: build clean test test-local install-all install-edge install-player install-connectorhost

# Build all collections
build:
	./build-all.sh

# Clean build artifacts
clean:
	rm -rf build/
	find . -name "*.tar.gz" -delete

# Test collections (requires ansible-test)
test:
	@for collection in edge player connectorhost; do \
		echo "Testing tulip.$$collection..."; \
		cd collections/ansible_collections/tulip/$$collection && \
		ansible-test sanity --python 3.8 || true; \
		cd - > /dev/null; \
	done

# Local development testing with mock server
test-local:
	@echo "Running local tests against mock server..."
	@if ! pgrep -f "mock_api_server.py" > /dev/null; then \
		echo "Starting mock server in background..."; \
		python testing/mock_api_server.py > /tmp/mock_server.log 2>&1 & \
		echo $$! > /tmp/mock_server.pid; \
		sleep 3; \
	fi
	@./testing/run_tests.sh
	@if [ -f /tmp/mock_server.pid ]; then \
		echo "Stopping mock server..."; \
		kill $$(cat /tmp/mock_server.pid) 2>/dev/null || true; \
		rm -f /tmp/mock_server.pid; \
	fi

# Install all collections from built artifacts
install-all: build
	@for file in build/tulip-*.tar.gz; do \
		echo "Installing $$file..."; \
		ansible-galaxy collection install "$$file" --force; \
	done

# Install specific collections from built artifacts
install-edge: build
	ansible-galaxy collection install build/tulip-edge-*.tar.gz --force

install-player: build
	ansible-galaxy collection install build/tulip-player-*.tar.gz --force

install-connectorhost: build
	ansible-galaxy collection install build/tulip-connectorhost-*.tar.gz --force

# Display help
help:
	@echo "Available targets:"
	@echo "  build                 - Build all collections"
	@echo "  clean                 - Remove build artifacts"
	@echo "  test                  - Run tests on all collections"
	@echo "  test-local           - Run local tests with mock server"
	@echo "  install-all          - Build and install all collections"
	@echo "  install-edge         - Build and install tulip.edge"
	@echo "  install-player       - Build and install tulip.player"
	@echo "  install-connectorhost - Build and install tulip.connectorhost"
	@echo "  help                 - Show this help message"
