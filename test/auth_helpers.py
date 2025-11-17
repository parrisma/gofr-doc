"""Utility functions for authenticated HTTP requests in tests

Provides helpers for adding JWT tokens to HTTP requests when calling
auth-enabled test servers.
"""

from typing import Dict, Optional
import httpx


def add_auth_header(token: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Add JWT token as Authorization Bearer header to request headers

    Args:
        token: JWT token string
        headers: Existing headers dict (optional)

    Returns:
        Dict with Authorization header added

    Example:
        headers = add_auth_header(test_jwt_token)
        response = httpx.get(url, headers=headers)
    """
    if headers is None:
        headers = {}
    headers["Authorization"] = f"Bearer {token}"
    return headers


async def authenticated_get(
    url: str, token: str, headers: Optional[Dict[str, str]] = None, **kwargs
) -> httpx.Response:
    """
    Make authenticated GET request with JWT token

    Args:
        url: URL to request
        token: JWT token string
        headers: Additional headers (optional)
        **kwargs: Additional arguments for httpx.get

    Returns:
        httpx.Response: Response object

    Example:
        response = await authenticated_get(
            f"{test_server_url}/api/documents",
            test_jwt_token
        )
    """
    headers = add_auth_header(token, headers)
    async with httpx.AsyncClient() as client:
        return await client.get(url, headers=headers, **kwargs)


async def authenticated_post(
    url: str, token: str, headers: Optional[Dict[str, str]] = None, **kwargs
) -> httpx.Response:
    """
    Make authenticated POST request with JWT token

    Args:
        url: URL to request
        token: JWT token string
        headers: Additional headers (optional)
        **kwargs: Additional arguments for httpx.post

    Returns:
        httpx.Response: Response object

    Example:
        response = await authenticated_post(
            f"{test_server_url}/api/documents",
            test_jwt_token,
            json={"content": "..."}
        )
    """
    headers = add_auth_header(token, headers)
    async with httpx.AsyncClient() as client:
        return await client.post(url, headers=headers, **kwargs)


async def authenticated_put(
    url: str, token: str, headers: Optional[Dict[str, str]] = None, **kwargs
) -> httpx.Response:
    """
    Make authenticated PUT request with JWT token

    Args:
        url: URL to request
        token: JWT token string
        headers: Additional headers (optional)
        **kwargs: Additional arguments for httpx.put

    Returns:
        httpx.Response: Response object
    """
    headers = add_auth_header(token, headers)
    async with httpx.AsyncClient() as client:
        return await client.put(url, headers=headers, **kwargs)


async def authenticated_delete(
    url: str, token: str, headers: Optional[Dict[str, str]] = None, **kwargs
) -> httpx.Response:
    """
    Make authenticated DELETE request with JWT token

    Args:
        url: URL to request
        token: JWT token string
        headers: Additional headers (optional)
        **kwargs: Additional arguments for httpx.delete

    Returns:
        httpx.Response: Response object
    """
    headers = add_auth_header(token, headers)
    async with httpx.AsyncClient() as client:
        return await client.delete(url, headers=headers, **kwargs)
