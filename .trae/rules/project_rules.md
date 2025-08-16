# OpenRouter Proxy Interceptor - Project Rules

Important: Use commands in the Makefile to install, run, clean, check, and test the project.

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

## Testing/Debugging
- **Manual Testing**: Run app, point client to `http://localhost:8080`
- **Log Analysis**: Check `proxy_interceptor.log` for detailed request traces

## Common Gotchas
- **Async Exceptions**: Wrap async calls with proper error handling (see `main.py` exception handling)
- **Signal Emissions**: Always check thread context before emitting signals
- **Resource Cleanup**: Ensure `AsyncRunner` loop is properly closed on exit