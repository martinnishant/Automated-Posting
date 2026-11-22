import httpx
import uvicorn

from app.main import app
from scripts.demo_run import mock_transport

transport = mock_transport()
real_client = httpx.AsyncClient


class DemoClient(real_client):
    def __init__(self, *args, **kwargs):
        kwargs["transport"] = transport
        super().__init__(*args, **kwargs)


httpx.AsyncClient = DemoClient

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4001)
