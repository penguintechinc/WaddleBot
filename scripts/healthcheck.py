#!/usr/bin/env python3
"""
Standard health check script for all Waddles containers.
Can be used in Dockerfiles and for manual testing.

Supports /health, /healthz, and /metrics endpoints.
"""
import sys
import urllib.request
import urllib.error


def check_health(url: str, timeout: int = 5) -> int:
    """
    Check health endpoint and return exit code.

    Args:
        url: Health check URL
        timeout: Request timeout in seconds

    Returns:
        0 for success, 1 for failure
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status == 200:
                data = response.read().decode('utf-8')
                print(f"✓ Health check passed: {url}")
                print(f"  Response: {data}")
                return 0
            else:
                print(f"✗ Health check failed: HTTP {response.status}")
                return 1
    except urllib.error.HTTPError as e:
        print(f"✗ Health check failed: HTTP {e.code} - {e.reason}")
        return 1
    except urllib.error.URLError as e:
        print(f"✗ Health check failed: {e.reason}")
        return 1
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: healthcheck.py <url>")
        print("Example: healthcheck.py http://localhost:8000/health")
        sys.exit(1)

    url = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    exit_code = check_health(url, timeout)
    sys.exit(exit_code)
