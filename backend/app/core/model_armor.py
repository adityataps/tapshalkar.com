import httpx
import google.auth
import google.auth.transport.requests


def _get_token() -> str:
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    return credentials.token


async def shield(text: str, template_name: str) -> tuple[bool, str]:
    """
    Sanitize user input via Google Cloud Model Armor.

    Returns (is_safe, reason_if_blocked).
    Fails open (returns True) on any API error so chat is never broken by
    a Model Armor outage.

    template_name format:
        projects/{project}/locations/{region}/templates/{template_id}
    """
    token = _get_token()
    url = f"https://modelarmor.googleapis.com/v1/{template_name}:sanitizeUserPrompt"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {"user_prompt_data": {"text": {"content": text}}}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(url, json=body, headers=headers)
        if r.status_code != 200:
            return True, ""  # fail open

        data = r.json()
        result = data.get("sanitizationResult", {})
        if result.get("filterMatchState") == "MATCH_FOUND":
            # Return the first matched filter name as the reason
            filter_results = result.get("filterResults", {})
            reason = next(iter(filter_results), "policy_violation")
            return False, reason

        return True, ""
    except Exception:
        return True, ""  # fail open on any error
