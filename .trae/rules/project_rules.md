# OpenRouter Proxy Interceptor - Project Rules

## Architecture Overview
- **GUI App**: PyQt6 desktop application with async proxy server
- **Dual Thread Model**: Qt GUI runs in main thread, FastAPI proxy runs in dedicated `AsyncRunner` thread
- **Primary Purpose**: Intercept HTTP traffic targeting OpenRouter API endpoints
- **Logging**: As this is a GUI application, add extensive logging to debug and monitor the application behavior.

## Key Components & Responsibilities
| Component | Purpose | Key Files |
|-----------|---------|-----------|
| **Main Entry** | Qt app initialization, logging setup | `proxy_interceptor/main.py` |
| **GUI Window** | Qt main window, proxy control, thread management | `proxy_interceptor/main_window.py` |
| **Proxy Engine** | FastAPI server routes request/response capture | `proxy_interceptor/proxy_server.py` |
| **Data Models** | Dataclasses for request/response structure | `proxy_interceptor/models.py` |
| **UI Widgets** | Request list & details visualization | `request_list_widget.py`, `request_details_widget.py` |

## Threading Patterns
- **Signal Bridge**: Use `pyqtSignal` to communicate between GUI and proxy threads
- **Async Runner**: `AsyncRunner()` creates dedicated asyncio loop in `QThread`
- **Thread Safety**: All proxy operations → emit signals → GUI thread handles updates

## Development Workflow
```bash
# Install deps (uv + PyQt6)
make install
# Run application
make run
```

## Coding Conventions
- **Async Asyncio**: Proxy functions use asyncio, httpx for external calls  
- **Qt Signal Pattern**: `pyqtSignal()` for cross-thread communication
- **Pydantic Dataclasses**: Use `@dataclass` for models (no Pydantic yet)
- **Logging**: Use `logger = logging.getLogger(__name__)` with DEBUG level
- **Configuration**: `@dataclass` based config as seen in `ProxyConfig`

## Integration Points
- **Proxy Target**: Hardcoded to `https://openrouter.ai/api/v1`
- **Port**: Default 8080 (configurable via `ProxyConfig`)
- **Request Capture**: All HTTP methods via FastAPI catch-all route `/{path:path}`
- **Logging**: `proxy_interceptor.log` + console output

## Testing/Debugging
- **Manual Testing**: Run app, point client to `http://localhost:8080`
- **Log Analysis**: Check `proxy_interceptor.log` for detailed request traces
- **UI Testing**: Use mock data (`mock_data.py:generate_mock_data()`) if needed

## Common Gotchas
- **Async Exceptions**: Wrap async calls with proper error handling (see `main.py` exception handling)
- **Signal Emissions**: Always check thread context before emitting signals
- **Resource Cleanup**: Ensure `AsyncRunner` loop is properly closed on exit