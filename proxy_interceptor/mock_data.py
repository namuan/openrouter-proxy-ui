from datetime import datetime
from .models import InterceptedRequest, HttpRequest, HttpResponse


def generate_mock_data():
    """Generate mock intercepted requests for testing."""
    return [
        InterceptedRequest(
            request=HttpRequest(
                timestamp=datetime.now(),
                method="GET",
                url="https://api.example.com/users",
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                    "Authorization": "Bearer token123"
                },
                body=""
            ),
            response=HttpResponse(
                status_code=200,
                status_text="OK",
                headers={
                    "Content-Type": "application/json",
                    "Content-Length": "1234"
                },
                body='{"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}'
            )
        ),
        InterceptedRequest(
            request=HttpRequest(
                timestamp=datetime.now(),
                method="POST",
                url="https://api.example.com/users",
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Content-Type": "application/json",
                    "Authorization": "Bearer token123"
                },
                body='{"name": "Charlie", "email": "charlie@example.com"}'
            ),
            response=HttpResponse(
                status_code=201,
                status_text="Created",
                headers={
                    "Content-Type": "application/json",
                    "Location": "/users/3"
                },
                body='{"id": 3, "name": "Charlie", "email": "charlie@example.com"}'
            )
        ),
        InterceptedRequest(
            request=HttpRequest(
                timestamp=datetime.now(),
                method="PUT",
                url="https://api.example.com/users/1",
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Content-Type": "application/json",
                    "Authorization": "Bearer token123"
                },
                body='{"name": "Alice Smith", "email": "alice@example.com"}'
            ),
            response=HttpResponse(
                status_code=200,
                status_text="OK",
                headers={
                    "Content-Type": "application/json"
                },
                body='{"id": 1, "name": "Alice Smith", "email": "alice@example.com"}'
            )
        ),
        InterceptedRequest(
            request=HttpRequest(
                timestamp=datetime.now(),
                method="DELETE",
                url="https://api.example.com/users/2",
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Authorization": "Bearer token123"
                },
                body=""
            ),
            response=HttpResponse(
                status_code=204,
                status_text="No Content",
                headers={},
                body=""
            )
        )
    ]
