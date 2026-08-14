#!/usr/bin/env python3
"""
Health check script for all services.

Checks connectivity and health of:
- PostgreSQL database
- Redis cache
- Temporal server
- Orchestrator API
"""

import asyncio
import sys
from typing import Any

import httpx
import redis
from sqlalchemy import text
from sqlmodel import create_engine

from apps.orchestrator.config import settings


async def check_database() -> tuple[bool, str]:
    """Check PostgreSQL database connectivity."""
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            if row and row[0] == 1:
                return True, "Database connection successful"
            return False, "Database query returned unexpected result"
    except Exception as e:
        return False, f"Database connection failed: {str(e)}"


async def check_redis() -> tuple[bool, str]:
    """Check Redis connectivity."""
    try:
        # Parse Redis URL
        r = redis.from_url(settings.redis_url)
        r.ping()
        return True, "Redis connection successful"
    except Exception as e:
        return False, f"Redis connection failed: {str(e)}"


async def check_temporal() -> tuple[bool, str]:
    """Check Temporal server connectivity."""
    try:
        # Temporal health check via HTTP
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{settings.temporal_host.replace(':7233', ':7233')}",
                timeout=5.0,
            )
            # Temporal doesn't have a standard health endpoint,
            # so we just check if the port is accessible
            return True, "Temporal server accessible"
    except Exception as e:
        # Alternative: just check if port is open
        try:
            import socket

            host, port = settings.temporal_host.split(":")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, int(port)))
            sock.close()
            if result == 0:
                return True, "Temporal server port accessible"
            return False, f"Temporal server port {port} not accessible"
        except Exception as inner_e:
            return False, f"Temporal connectivity check failed: {str(inner_e)}"


async def check_api() -> tuple[bool, str]:
    """Check Orchestrator API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{settings.api_host}:{settings.api_port}/health", timeout=5.0
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    return True, "API health check passed"
                return False, f"API unhealthy: {data}"
            return False, f"API returned status code {response.status_code}"
    except httpx.ConnectError:
        return False, "API not running (connection refused)"
    except Exception as e:
        return False, f"API health check failed: {str(e)}"


def print_status(service: str, healthy: bool, message: str) -> None:
    """Print service status with color formatting."""
    status = "✓" if healthy else "✗"
    color = "\033[92m" if healthy else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{status}{reset} {service:<20} {message}")


async def main() -> int:
    """Run all health checks."""
    print("Enterprise Agent Orchestrator - Health Check")
    print("=" * 60)
    print()

    checks = [
        ("PostgreSQL", check_database),
        ("Redis", check_redis),
        ("Temporal", check_temporal),
        ("Orchestrator API", check_api),
    ]

    results = []
    for service_name, check_func in checks:
        healthy, message = await check_func()
        print_status(service_name, healthy, message)
        results.append(healthy)

    print()
    print("=" * 60)

    all_healthy = all(results)
    if all_healthy:
        print("✓ All services are healthy")
        return 0
    else:
        failed_count = sum(1 for r in results if not r)
        print(f"✗ {failed_count} service(s) unhealthy")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
