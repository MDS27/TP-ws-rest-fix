import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount, WebSocketRoute
from starlette.requests import Request #REST (GET)
from starlette.exceptions import HTTPException
from starlette.templating import Jinja2Templates #Создание шаблонов страниц
from starlette.staticfiles import StaticFiles #Готовые стили оформления
from starlette.websockets import WebSocket
from starlette.endpoints import HTTPEndpoint, WebSocketEndpoint
from fix_server import ServerFixEP,FixEP
import random
import towns

from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from starlette.responses import Response

from sqlalchemy.orm.exc import NoResultFound
from models.dataBase import createDB, sessionDB
from models.userModel import Users

createDB()

# pip install 'uvicorn[standard]'

templates = Jinja2Templates(directory='templates')
class WebSocketEP(WebSocketEndpoint):
    encoding = "text"
    registered_sockets = set()

    async def on_connect(self, websocket: WebSocket):
        await websocket.accept()
        self.registered_sockets.add((websocket))
        self.gameState = 'None'
        self.townO = towns.town()
        self.botTown = 'None'

    async def on_receive(self, websocket: WebSocket, data):
        if data == ' ':
            self.gameState = 'None'
            await websocket.send_text(f"User:")
        else:
            await websocket.send_text(f"User: {data}") #Возврат исходного сообщения
            if data == '/старт':
                self.gameState = 'None'
                await websocket.send_text(f"Bot: Привет! Сыграем в игру?")
                await websocket.send_text(f"/кнб - Камень-Ножницы-Бумага")
                await websocket.send_text(f"/оир - Орел и Решка")
                await websocket.send_text(f"/гр - Города России")
            elif data == '/кнб':
                self.gameState = 'кнб'
                await websocket.send_text(f"Bot: Камень, Ножницы, Бумага. Раз, Два, Три!")
            elif data == '/оир':
                self.gameState = 'оир'
                await websocket.send_text("Bot: Выбирай: Орел или Решка")
            elif data == '/гр':
                self.gameState = 'гр'
                self.botTown = 'Москва'
                await websocket.send_text(f"Bot: Я начну, если захочешь закончить, напиши \'стоп\'")
                await websocket.send_text(f"Bot: Москва, тебе на А")
                self.townO.startGR()
            elif self.gameState == 'гр':
                if data in ['стоп', 'Стоп']:
                    self.gameState = 'None'
                    await websocket.send_text(f"Bot: Хорошо, заканчиваем")
                else:
                    town = self.userStepGR(data)
                    if town == 'повтор':
                        await websocket.send_text(f"Bot: Этот город уже был")
                    elif town:
                        await websocket.send_text(f"Bot: {self.botStepGR(data)}")
                    else:
                        await websocket.send_text(f"Bot: Некорректный город, попробуй изменить ответ")
            elif self.gameState == 'кнб':
                self.gameState = 'None'
                hand = self.knbHand()
                await websocket.send_text(f"Bot: {hand}")
                await websocket.send_text(f"Bot: {self.knbRes(data,hand)}")
            elif self.gameState == 'оир':
                self.gameState = 'None'
                await websocket.send_text(f"Bot: {self.oir(data)}")
            else:
                pass

    async def on_disconnect(self, websocket: WebSocket, close_code: int):
        self.registered_sockets.remove(websocket)

    def oir(self, data):
        if data in ['Орел', 'орел', 'Орёл', 'орёл']:
            data = 'Орел'
        elif data in ['Решка', 'решка']:
            data = 'Решка'
        else:
            data = 'Это не по правилам'
            return data
        coin = random.randrange(0, 2)
        if coin == 0:
            coin = 'Орел'
        else:
            coin = 'Решка'
        if coin == data:
            coin +=', Ты победил!'
            return coin
        else:
            coin += ', Не повезло!'
            return coin

    def knbHand(self):
        hand = random.randrange(0, 3)
        if hand == 0:
            data = 'Камень'
            return data
        elif hand == 1:
            data = 'Ножницы'
            return data
        else:
            data = 'Бумага'
            return data

    def knbRes(self,data,hand):
        if data in ['Камень', 'камень']:
            data = 'Камень'
        elif data in ['Ножницы', 'ножницы']:
            data = 'Ножницы'
        elif data in ['Бумага','бумага']:
            data = 'Бумага'
        else:
            data = 'Это не по правилам'
            return data
        if data == hand:
            data = 'Ничья!'
            return data
        elif (data == 'Камень' and hand == 'Бумага') or (data == 'Ножницы' and hand == 'Камень') or (data == 'Бумага' and hand == 'Ножницы'):
            data = 'Я победил!'
            return data
        else:
            data = 'Ты победил!'
            return data

    def botStepGR(self, data):
        newTown = self.townO.botAskToBase(data)
        if newTown != 'повтор':
            self.botTown = newTown
            return newTown
        else:
            if data[len(data) - 1] in ['ы', 'ё', 'ъ', 'ь']:
                data = 'Сдаюсь, я не помню больше городов на ' + data[len(data)-2]
            else:
                data = 'Сдаюсь, я не помню больше городов на ' + data[len(data)-1]
            self.gameState = 'None'
            return data

    def userStepGR(self, data):
        if self.botTown[len(self.botTown)-1] in ['ы', 'ё', 'ъ', 'ь']:
            sign = self.botTown[len(self.botTown)-2].upper()
        else:
            sign = self.botTown[len(self.botTown)-1].upper()
        res = self.townO.userAskToBase(data, sign)
        if res == 'повтор':
            return res
        return res

    @classmethod
    async def broadcast(self, data: bytes):
        for socket in self.registered_sockets:
            await socket.send_text(f"{data}")

class ChatEP(HTTPEndpoint):
    async def get(self, request):
        st = request.session.get('auth') #проверка аутентификации
        if st != 'auth':
            return RedirectResponse(url="/login")
        name = request.session.get('name')
        template = "chat.html"
        context = {"request": request, "Username": name}
        return templates.TemplateResponse(template, context)

    async def post(self, request):
        form = await request.form()
        message = form['broadcast_form_message']
        await WebSocketEP.broadcast(message)
        return Response()

class ChatBotEP(HTTPEndpoint):
    async def get(self, request):
        st = request.session.get('auth') #проверка аутентификации
        if st != 'auth':
            return RedirectResponse(url="/login")
        name = request.session.get('name')
        template = "chatBot.html"
        context = {"request": request, "Username": name}
        return templates.TemplateResponse(template, context)

class LoginEP(HTTPEndpoint):
    async def get(self, request):
        st = request.session.get('auth') #проверка аутентификации
        if st == 'auth':
            return RedirectResponse(url="/account")
        template = "login.html"
        context = {"request": request}
        return templates.TemplateResponse(template, context)

    async def post(self, request):
        form = await request.form()
        name = form["login_Text"]
        password = form["password_Text"]
        loginSession = sessionDB()
        # проверка
        try:
            testuser = loginSession.query(Users).filter_by(username=name,password=password).one()
        except NoResultFound:
            # ошибка входа
            request.session.clear()
            return Response()
        request.session.update({'name': name})
        request.session.update({'auth': 'auth'})
        return Response()

class Sign_inEP(HTTPEndpoint):
    async def get(self, request):
        st = request.session.get('auth') #проверка аутентификации
        if st == 'auth':
            return RedirectResponse(url="/account")
        template = "sign_in.html"
        context = {"request": request}
        return templates.TemplateResponse(template, context)

    async def post(self, request):
        form = await request.form()
        name = form["sign_in_Text"]
        password = form["password_Text"]

        # регистрация
        signinSession = sessionDB()
        try:
            testuser = signinSession.query(Users).filter_by(username=name).one()
            print('такой пользователь уже есть')
            return Response()
        except NoResultFound:
            user = Users(username=name, password=password, description="Add description")
            signinSession.add(user)
            signinSession.commit()
            request.session.update({'name': name})
            request.session.update({'auth':'auth'})
            print(request.session.get('name'))
            return Response()

class AccountEP(HTTPEndpoint):
    async def get(self, request):
        st = request.session.get('auth')
        if st != 'auth':
            return RedirectResponse(url="/login")
        name = request.session.get('name')
        accountSession = sessionDB()
        accountData = accountSession.query(Users).filter_by(username=name).one()
        description = accountData.description
        template = "account.html"
        context = {"request": request, "Username": name, "Description" : description}
        return templates.TemplateResponse(template, context)

    async def post(self, request):
        try:
            form = await request.form()
            name = form["description_User"]
            description = form["description_Text"]
            descriptionSession = sessionDB()
            try:
                descriptionUser = descriptionSession.query(Users).filter_by(username=name).one()
                descriptionUser.description = description
                descriptionSession.add(descriptionUser)
                descriptionSession.commit()
                return Response()
            except NoResultFound:
                return Response()

        except Exception:
            try:
                form = await request.form()
                name = form["delete_Text"]
                password = form["password_Text"]
                deleteSession = sessionDB()
            except Exception:
                print('выход')
                request.session.clear()
            return Response()



async def homepage(request):
    name = request.session.get('name') or "Account"
    template = "index.html"
    context = {"request": request,"Username": name}
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
    Route('/', homepage, name="homepage"),
    Mount('/static', app=StaticFiles(directory="statics"), name="static"),
    WebSocketRoute('/ws', WebSocketEP, name="ws"),
    Route('/chat', ChatEP, methods=['GET','POST'], name="chat"),
    Route('/chatBot', ChatBotEP, name="chatBot"),
    Route('/login', LoginEP,methods=['GET','POST'], name="login"),
    Route('/sign_in', Sign_inEP,methods=['GET','POST'], name="sign_in"),
    Route('/account', AccountEP, methods=['GET','POST'], name="account"),
    WebSocketRoute('/fix',ServerFixEP,name="fix"),
    Route('/fixPage',FixEP, name="fixPage"),
]

exceptions = {
    404: not_found,
    500: server_error
}

middleware = [Middleware(SessionMiddleware,secret_key="HfkjbUE6d7UIE9cV69cUb9BIC8")]
app = Starlette(debug=True, routes=routes, exception_handlers = exceptions, middleware=middleware)


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000)



