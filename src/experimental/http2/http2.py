#!/bin/python3

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request

import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve


async def homepage(request: Request):
    return JSONResponse({
        'path': str(request.url.path),
        'query': str(request.url.query)
    })


async def api(request: Request):
    return JSONResponse({
        'api': "true",
        'path': str(request.url.path),
        'query': str(request.url.query)
    })

if __name__ == '__main__':
    # ORDER MATTERS
    # https://www.starlette.io/routing/
    routes = [
        Route("/api/{path:path}", endpoint=api, methods=["GET", "POST"]),
        Route("/{path:path}", endpoint=homepage, methods=["GET"])
    ]

    config: Config = Config()
    config.bind = ["localhost:8930"]
    config.certfile = "working/certs/cert.pem"
    config.keyfile = "working/certs/key.pem"

    app = Starlette(debug=True, routes=routes)
    asyncio.run(serve(app=app, config=config))

    # Cannot Work Without Disabling __main__ check
    # hypercorn --certfile working/certs/cert.pem --keyfile working/certs/key.pem --bind localhost:8930 experimental/http2/http2:app
