.PHONY: install run dev clean lint format test icons

# Install dependencies
install:
	@uv sync
	@uv run pre-commit install

# Run the application
run:
	@uv run python -m proxy_interceptor.main

# Clean build artifacts
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -delete
	rm -rf build/ dist/
	@uvx pyclean .

# Package the application
package: clean
	uv run pyinstaller proxy_interceptor.spec --clean

install-macosx: package ## Installs application in users Application folder
	./scripts/install-macosx.sh OpenRouterProxy.app

start-work: ## Start working on a new feature
	@echo "🚀 Starting work on a new feature"
	@mob start -i -b "$(FEATURE)"

# Check code (lint and format)
check: ## Run code quality tools.
	@echo "🚀 Checking lock file consistency with 'pyproject.toml'"
	@uv lock --locked
	@echo "🚀 Linting code: Running pre-commit"
	@uv run pre-commit run -a
	@mob next

# Run tests (placeholder for future tests)
test: ## Run all unit tests
	@echo "🚀 Running unit tests"
	@uv run pytest -v

test-single: ## Run a single test file (usage: make test-single TEST=test_config.py)
	@echo "🚀 Running single test: $(TEST)"
	@uv run pytest -v tests/$(TEST)

# Generate high-resolution icons
icons:
	./generate_icon.sh assets/or-proxy.png or-proxy

# Help target
help:
	@echo "Available targets:"
	@echo "  install - Install dependencies"
	@echo "  run     - Run the application"
	@echo "  clean   - Clean build artifacts"
	@echo "  check   - Run checks"
	@echo "  test    - Run tests"
	@echo "  icons   - Generate high-resolution icons from PNG source"
	@echo "  help    - Show this help"
