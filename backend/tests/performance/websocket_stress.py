"""WebSocket stress test (H5.2).

Usage: python tests/performance/websocket_stress.py
"""

import asyncio
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def connect_and_listen(url: str, token: str, duration: int = 30, client_id: int = 0):
    """Connect a WebSocket client and maintain connection for `duration` seconds."""
    try:
        import websockets
    except ImportError:
        logger.error("websockets package required: pip install websockets")
        return False

    try:
        async with websockets.connect(f"{url}?token={token}") as ws:
            start = time.time()
            pings = 0
            while time.time() - start < duration:
                await ws.send("ping")
                response = await ws.recv()
                assert response == "pong", f"Expected 'pong', got '{response}'"
                pings += 1
                await asyncio.sleep(0.5)
            logger.debug(f"Client {client_id}: {pings} pings in {duration}s")
            return True
    except Exception as e:
        logger.warning(f"Client {client_id} error: {e}")
        return False


async def stress_test(
    base_url: str = "ws://localhost:8000",
    num_connections: int = 50,
    duration: int = 30,
):
    """Run WebSocket stress test with N concurrent connections."""
    # Get auth token
    try:
        import httpx
    except ImportError:
        logger.error("httpx package required: pip install httpx")
        return

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:8000/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin123"},
        )
        if resp.status_code != 200:
            logger.error(f"Login failed: {resp.status_code}")
            return
        token = resp.json().get("access_token", "")

    logger.info(f"Starting {num_connections} WebSocket connections for {duration}s...")
    start = time.time()

    tasks = [
        connect_and_listen(f"{base_url}/ws/orders", token, duration, i)
        for i in range(num_connections)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.time() - start
    successes = sum(1 for r in results if r is True)
    failures = num_connections - successes

    logger.info(f"Results: {successes}/{num_connections} connections survived {duration}s")
    logger.info(f"Elapsed: {elapsed:.1f}s, Failures: {failures}")


if __name__ == "__main__":
    asyncio.run(stress_test())
