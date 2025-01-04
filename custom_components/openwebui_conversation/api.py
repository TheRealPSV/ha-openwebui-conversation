"""OpenWebUI API Client."""

from __future__ import annotations

import asyncio
import socket

import aiohttp
import async_timeout

from .exceptions import ApiClientError, ApiCommError, ApiJsonError, ApiTimeoutError


class OpenWebUIApiClient:
    """OpenWebUI API Client."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int,
        verify_ssl: bool,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.timeout = timeout
        self._verify_ssl = verify_ssl
        self._session = session

    async def async_get_heartbeat(self) -> bool:
        """Get heartbeat from the API."""
        response = await self._api_wrapper(method="get", url=f"{self._base_url}/health")
        return response["status"] == True

    async def async_get_models(self) -> any:
        """Get models from the API."""
        return await self._api_wrapper(
            method="get",
            url=f"{self._base_url}/api/models",
            headers={
                "Content-type": "application/json; charset=UTF-8",
                "Authorization": f"Bearer {self._api_key}",
            },
        )

    async def async_generate_search_query(
        self,
        data: dict | None = None,
    ) -> any:
        """Generate a completion from the API."""
        return await self._api_wrapper(
            method="post",
            url=f"{self._base_url}/api/task/queries/completions",
            data=data,
            headers={
                "Content-type": "application/json; charset=UTF-8",
                "Authorization": f"Bearer {self._api_key}",
            },
        )

    async def async_perform_search(
        self,
        data: dict | None = None,
    ) -> any:
        """Generate a completion from the API."""
        return await self._api_wrapper(
            method="post",
            url=f"{self._base_url}/retrieval/api/v1/process/web/search",
            data=data,
            headers={
                "Content-type": "application/json; charset=UTF-8",
                "Authorization": f"Bearer {self._api_key}",
            },
        )

    async def async_generate(
        self,
        data: dict | None = None,
    ) -> any:
        """Generate a completion from the API."""
        return await self._api_wrapper(
            method="post",
            url=f"{self._base_url}/ollama/api/chat",
            data=data,
            headers={
                "Content-type": "application/json; charset=UTF-8",
                "Authorization": f"Bearer {self._api_key}",
            },
        )

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
        decode_json: bool = True,
    ) -> any:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(self.timeout):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    verify_ssl=self._verify_ssl,
                )

                if response.status == 404 and decode_json:
                    json = await response.json()
                    raise ApiJsonError(json["error"])

                response.raise_for_status()

                if decode_json:
                    return await response.json()
                return await response.text()
        except ApiJsonError as e:
            raise e
        except asyncio.TimeoutError as e:
            raise ApiTimeoutError("timeout while talking to the server") from e
        except (aiohttp.ClientError, socket.gaierror) as e:
            raise ApiCommError("unknown error while talking to the server") from e
        except Exception as e:  # pylint: disable=broad-except
            raise ApiClientError("something really went wrong!") from e
