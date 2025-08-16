# OpenRouter Proxy Interceptor — Improvement Tasks Checklist

Use this checklist to track architectural and code-level improvements. Items are ordered to reduce risk and build on foundations first. Each task is actionable and specific. Check [ ] to [x] when completed.

2. [ ] Logging hardening and observability
   - [ ] Ensure a single logging configuration point (avoid duplicate basicConfig calls if app embedded)
   - [ ] Add rotating file handler (size/time-based) to avoid unbounded proxy_interceptor.log growth
   - [ ] Mask sensitive values (API keys, auth tokens) in all logs
   - [ ] Add FastAPI middleware for request timing and error logging

3. [ ] Configuration management/validation
   - [ ] Introduce a pydantic model (or dataclass + validation) for persisted config (api_keys, api_models, port, tokens)
   - [ ] Validate port range and availability before saving/starting server; show user-friendly error
   - [ ] Validate API keys format (basic prefix check) and prevent saving empty config
   
4. [ ] Threading and async lifecycle robustness
   - [ ] Ensure AsyncRunner loop is always stopped and closed (handle edge cases on app exit)
   - [ ] Guard against multiple proxy starts; disable Start button while starting
   - [ ] Propagate fatal proxy start errors to GUI with actionable guidance
   - [ ] Add retry with backoff for uvicorn startup failures (port in use, permission)
   - [ ] Confirm thread-safety of signals and data (only emit from AsyncRunner thread via pyqtSignal)

5. [ ] Proxy server resilience and correctness
   - [ ] Add timeout, retry, and backoff policy for httpx client (429 and transient network errors)
   - [ ] Respect Retry-After headers for 429 responses
   - [ ] Make target_base_url configurable (environment + UI hidden/advanced)
   - [ ] Add health endpoint /healthz that checks upstream connectivity (optional ping)
   - [ ] Add readiness endpoint /ready that reflects uvicorn state and client init
   - [ ] Implement graceful shutdown sequence with deadlines

7. [ ] Data model and storage enhancements
   - [ ] Add stable request ID, timestamps, and derived fields (duration, model, error type)
   - [ ] Add a lightweight ring buffer limit (configurable) to cap memory usage of intercepted_requests
   - [ ] Add export/import of captured sessions (JSONL or NDJSON) via UI

8. [ ] UI/UX improvements for productivity
   - [ ] Show streaming progress indicator and total tokens/latency metadata

9. [ ] Security and privacy safeguards
   - [ ] Never log or display full API keys (ensure masking is consistent everywhere)
   - [ ] Add redaction of secrets in captured headers/body (Authorization, cookies)
   - [ ] Add explicit disclaimer and toggle to enable/disable body capture
   - [ ] Validate and sanitize file paths used for saving configs and exports

10. [ ] Error handling and user feedback
    - [ ] Centralize error handling utilities; convert exceptions to user-friendly messages
    - [ ] Display non-blocking toasts/snackbars for operations (save, start, stop, copy)
    - [ ] Add detailed guidance for common failures (no keys, model not available, port in use)

11. [ ] Performance tuning
    - [ ] Replace list with deque for intercepted_requests where appropriate
    - [ ] Batch UI updates when ingesting many requests to avoid signal storms
    - [ ] Consider virtualized list widget for large sessions
    - [ ] Profile httpx and UI operations; set reasonable default timeouts
