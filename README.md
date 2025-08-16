# OpenRouter Proxy Interceptor

A desktop GUI application that creates a local HTTP proxy server to intercept, inspect, and forward OpenRouter chat-completion requests.  
It transparently rotates between multiple API keys and free models, retries on failures, and logs every request/response pair.

![](docs/screenshot.png)

| ⚡ Quick start | 1. Install → 2. Paste OpenRouter keys → 3. Pick free models → 4. Click “Start Proxy” |
|---------------|----------------------------------------------------------------------------------------|

## Features

- **Rotate between Multiple API Keys and Free Models**  
  – Load any number of OpenRouter API keys and choose from free models.  
  – Requests are load-balanced; failed calls are retried with the next key / model.

- **Real-time request inspector**  
  – Complete request/response headers and bodies (pretty-printed JSON, XML, HTML).  
  — Streaming responses are captured and re-assembled for easy reading.

