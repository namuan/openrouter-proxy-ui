# OpenRouter Proxy Interceptor — Improvement Tasks Checklist

Use this checklist to track architectural and code-level improvements. Items are ordered to reduce risk and build on foundations first. Each task is actionable and specific. Check [ ] to [x] when completed.

2. [x] Logging hardening and observability
   - [x] Ensure a single logging configuration point (avoid duplicate basicConfig calls if app embedded)
   - [x] Add rotating file handler (size/time-based) to avoid unbounded proxy_interceptor.log growth
   - [x] Mask sensitive values (API keys, auth tokens) in all logs
   - [x] Add FastAPI middleware for request timing and error logging

3. [x] Configuration management/validation
   - [x] Introduce a pydantic model (or dataclass + validation) for persisted config (api_keys, api_models, port, tokens)
   - [x] Validate port range and availability before saving/starting server; show user-friendly error
   - [x] Validate API keys format (basic prefix check) and prevent saving empty config
   
4. [x] Threading and async lifecycle robustness
   - [x] Ensure AsyncRunner loop is always stopped and closed (handle edge cases on app exit)
   - [x] Guard against multiple proxy starts; disable Start button while starting
   - [x] Propagate fatal proxy start errors to GUI with actionable guidance
   - [x] Add retry with backoff for uvicorn startup failures (port in use, permission)
   - [x] Confirm thread-safety of signals and data (only emit from AsyncRunner thread via pyqtSignal)

5. [x] Proxy server resilience and correctness
   - [x] Add timeout, retry, and backoff policy for httpx client (429 and transient network errors)
   - [x] Respect Retry-After headers for 429 responses
   - [x] Make target_base_url configurable (environment + UI hidden/advanced)
   - [x] Add health endpoint /healthz that checks upstream connectivity (optional ping)
   - [x] Add readiness endpoint /ready that reflects uvicorn state and client init
   - [x] Implement graceful shutdown sequence with deadlines

8. [X] UI/UX improvements for productivity
   - [X] Show streaming progress indicator and total tokens/latency metadata

9. [X] Security and privacy safeguards
- [X] Never log or display full API keys (ensure masking is consistent everywhere)
- [x] Add redaction of secrets in captured headers/body (Authorization, cookies)
- [X] Add explicit disclaimer and toggle to enable/disable body capture
- [X] Validate and sanitize file paths used for saving configs and exports

10. [x] Error handling and user feedback
    - [x] Centralize error handling utilities; convert exceptions to user-friendly messages
    - [x] Display non-blocking toasts/snackbars for operations (save, start, stop, copy)
    - [x] Add detailed guidance for common failures (no keys, model not available, port in use)

11. [x] Performance tuning
    - [x] Replace list with deque for intercepted_requests where appropriate
    - [x] Batch UI updates when ingesting many requests to avoid signal storms
    - [ ] Consider virtualized list widget for large sessions
    - [x] Profile httpx and UI operations; set reasonable default timeouts
