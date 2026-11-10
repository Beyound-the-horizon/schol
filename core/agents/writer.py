import inspect
import logging
import os
from typing import Any, List, Union
import httpx
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

try:
    from core.schemas import ScholarshipCreate
except ImportError:
    from schemas import ScholarshipCreate

logger = logging.getLogger("core.agents.writer")


def get_api_config() -> tuple[str, str]:
    """Retrieve API Base URL and Ingestion Token from environment.
    
    Defaults:
    - API_BASE_URL: http://127.0.0.1:8000/api/v1
    - INGESTION_TOKEN: from .env INGESTION_TOKEN
    """
    base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
    token = os.getenv("INGESTION_TOKEN", "dev-secret-ingestion-token-change-me")
    return base_url, token


async def _submit_batch_async(
    client: httpx.AsyncClient, endpoint: str, payload: dict, headers: dict
) -> dict[str, Any]:
    response = await client.post(endpoint, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        return {
            "status": "auth_error",
            "error": "Unauthorized: Invalid or missing X-Ingestion-Token",
            "status_code": 401,
        }
    elif response.status_code == 422:
        return {
            "status": "validation_error",
            "error": response.json().get("detail", "Payload validation failed"),
            "status_code": 422,
        }
    else:
        return {
            "status": "http_error",
            "status_code": response.status_code,
            "error": response.text,
        }


def _submit_batch_sync(
    client: httpx.Client, endpoint: str, payload: dict, headers: dict
) -> dict[str, Any]:
    response = client.post(endpoint, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        return {
            "status": "auth_error",
            "error": "Unauthorized: Invalid or missing X-Ingestion-Token",
            "status_code": 401,
        }
    elif response.status_code == 422:
        return {
            "status": "validation_error",
            "error": response.json().get("detail", "Payload validation failed"),
            "status_code": 422,
        }
    else:
        return {
            "status": "http_error",
            "status_code": response.status_code,
            "error": response.text,
        }


def submit_scholarship_batch(
    records: List[ScholarshipCreate],
    client: Union[httpx.Client, httpx.AsyncClient, None] = None,
) -> Union[dict[str, Any], Any]:
    """Submit a batch of validated scholarship records to the FastAPI ingestion endpoint.
    
    Supports both synchronous and asynchronous callers:
    - If client is an AsyncClient, returns a coroutine.
    - If client is a synchronous Client (or None), runs synchronously and returns a dict.
    
    Endpoint: POST /api/v1/scholarships/ingest
    Header: X-Ingestion-Token: <token>
    """
    if not records:
        return {"status": "skipped", "message": "No records to submit", "total": 0}

    base_url, token = get_api_config()
    endpoint = f"{base_url}/scholarships/ingest"

    payload = {
        "items": [rec.model_dump(mode="json") for rec in records]
    }
    headers = {
        "X-Ingestion-Token": token,
        "Content-Type": "application/json",
    }

    if isinstance(client, httpx.AsyncClient):
        return _submit_batch_async(client, endpoint, payload, headers)

    own_client = client is None
    http_client = client or httpx.Client(timeout=30.0)

    try:
        return _submit_batch_sync(http_client, endpoint, payload, headers)
    except Exception as exc:
        logger.error("Failed to connect to ingestion API at %s: %s", endpoint, exc)
        return {
            "status": "connection_error",
            "error": f"{type(exc).__name__}: {exc}",
        }
    finally:
        if own_client:
            http_client.close()


def _parse_writer_result(
    batch_result: dict[str, Any], structured_record: ScholarshipCreate
) -> dict[str, Any]:
    results = batch_result.get("results", [])
    if results:
        res = results[0]
        rec_status = res.get("status")
        if rec_status in ("created", "updated"):
            return {
                "status": rec_status,
                "id": res.get("id"),
                "name": structured_record.name,
                "official_url": str(structured_record.official_url),
                "message": res.get("message"),
            }
        else:
            return {
                "status": "rejected",
                "reason": res.get("message", f"Backend rejected record with status {rec_status}"),
                "name": structured_record.name,
            }

    if "error" in batch_result:
        return {
            "status": "error",
            "reason": batch_result["error"],
            "name": structured_record.name,
        }

    return {
        "status": "error",
        "reason": f"Unexpected backend response: {batch_result}",
        "name": structured_record.name,
    }


def write_scholarship(
    structured_record: ScholarshipCreate | None,
    client: Union[httpx.Client, httpx.AsyncClient, None] = None,
) -> Union[dict[str, Any], Any]:
    """Writer Agent: Gatekeeper and client for FastAPI Ingestion API.
    
    Submits structured scholarship records via POST /api/v1/scholarships/ingest
    with authentication via X-Ingestion-Token.
    
    Supports both sync and async callers seamlessly.
    """
    if not structured_record:
        return {
            "status": "rejected",
            "reason": "Record is empty or failed schema validation.",
        }

    if not structured_record.name or len(structured_record.name.strip()) < 2:
        return {
            "status": "rejected",
            "reason": "Missing or invalid scholarship name.",
        }

    if not structured_record.official_url:
        return {
            "status": "rejected",
            "reason": "Missing official verification URL.",
        }

    if isinstance(client, httpx.AsyncClient):
        async def _async_write():
            res = await submit_scholarship_batch([structured_record], client=client)
            return _parse_writer_result(res, structured_record)
        return _async_write()

    batch_result = submit_scholarship_batch([structured_record], client=client)
    return _parse_writer_result(batch_result, structured_record)
