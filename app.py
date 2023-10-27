import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount, WebSocketRoute
from starlette.requests import Request #REST (GET)
from starlette.exceptions import HTTPException
from starlette.templating import Jinja2Templates #Создание шаблонов страниц
from starlette.staticfiles import StaticFiles #Готовые стили оформления
from starlette.websockets import WebSocket
from starlette.endpoints import HTTPEndpoint, WebSocketEndpoint

# pip install 'uvicorn[standard]'
templates = Jinja2Templates(directory='templates')



class WebSocketEP(WebSocketEndpoint):
    encoding = "text"

    async def on_connect(self, websocket: WebSocket):
        await websocket.accept()

    async def on_receive(self, websocket: WebSocket, data: bytes):
        await websocket.send_text(f"User: {data}")

    async def on_disconnect(self, websocket: WebSocket, close_code: int):
        pass

class ChatEP(HTTPEndpoint):
    async def get(self, request):
        template = "chat.html"
        context = {"request": request}
        return templates.TemplateResponse(template, context)

async def homepage(request):
    template = "index.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context)

async def not_found(request: Request, exc: HTTPException):
    template = "404.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context, status_code=404)

async def server_error(request: Request, exc: HTTPException):
    template = "500.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context, status_code=500)

routes = [
    Route('/', homepage),
    Mount('/static', app=StaticFiles(directory='statics'), name='static'),
    WebSocketRoute('/ws', WebSocketEP, name="ws"),
    Route('/chat', ChatEP, name="chat")
]

exceptions = {
    404: not_found,
    500: server_error
}


app = Starlette(debug=True, routes=routes, exception_handlers=exceptions)


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)