from __future__ import annotations

import asyncio
import logging

import uvicorn

from .bot import main as bot_main
from .db import startup_db
from .web import app


async def _serve() -> None:
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    await startup_db()
    await asyncio.gather(_serve(), bot_main())


if __name__ == "__main__":
    asyncio.run(main())
