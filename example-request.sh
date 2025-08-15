curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dummy-key" \
  -d '{
    "model": "openai/gpt-oss-20b:free",
    "messages": [{"role": "user", "content": "Hello"}]
  }'