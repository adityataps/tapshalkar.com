import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.anyio
async def test_contact_sends_email():
    mock_response = MagicMock()
    mock_response.id = "email-id-123"

    with patch("resend.Emails.send", return_value=mock_response):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/contact", json={
                "name": "Test User",
                "email": "test@example.com",
                "message": "Hello!",
            })

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.anyio
async def test_contact_rejects_missing_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/contact", json={"name": "No Email"})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_contact_rejects_invalid_email():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/contact", json={
            "name": "Bad Email",
            "email": "not-an-email",
            "message": "test",
        })
    assert response.status_code == 422
