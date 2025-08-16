.PHONY: install run dev clean lint format test

# Install dependencies
install:
	uv sync

# Run the application
run:
	uv run python -m proxy_interceptor.main

# Clean build artifacts
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -delete

# Lint code
lint:
	uv run ruff check .
	uv run ruff format --check .

# Format code
format:
	uv run ruff format .

# Run tests (placeholder for future tests)
test:
	uv run pytest

# Help target
help:
	@echo "Available targets:"
	@echo "  install - Install dependencies"
	@echo "  run     - Run the application"
	@echo "  clean   - Clean build artifacts"
	@echo "  lint    - Run linting checks"
	@echo "  format  - Format code"
	@echo "  test    - Run tests"
	@echo "  help    - Show this help"
