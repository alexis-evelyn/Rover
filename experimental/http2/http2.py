from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve


async def homepage(request):
    return JSONResponse({'hello': 'world'})


# TODO: Figure Out How To Get Truly Dynamic URLs
# https://www.starlette.io/routing/
routes = [
    Route("/", endpoint=homepage)
]

app = Starlette(debug=True, routes=routes)

# TODO: Figure Out How To Use These Settings In App
# hypercorn --certfile working/certs/cert.pem --keyfile working/certs/key.pem --bind localhost:8000 experimental/http2:app
# asyncio.run(serve(app, Config()))