from starlette.endpoints import HTTPEndpoint, WebSocketEndpoint
from starlette.websockets import WebSocket
from starlette.templating import Jinja2Templates #Создание шаблонов страниц

import simplefix
from simplefix import FixMessage, FixParser
import datetime
from decimal import Decimal
from uuid import uuid4
import re

import random

templates = Jinja2Templates(directory = 'templates')
class ServerFixEP(WebSocketEndpoint):
    encoding = "bytes"
    async def on_connect(self, websocket: WebSocket):
        await websocket.accept()

    async def on_receive(self, websocket: WebSocket, data: bytes):
        await websocket.send_bytes(self.run(data))
        print(data)
        if re.search('150=F', data.decode()) and re.search('39=2', data.decode()):
            await websocket.send_bytes(self.run(data, 1))
    async def on_disconnect(self, websocket: WebSocket, close_code: int):
        pass

    def run(self, data, rec = None):
        self.parser = FixParser()
        self.parser.append_buffer(data)
        self.msg = self.parser.get_message()
        send_time_str = datetime.datetime.utcnow().strftime('%Y%m%d-%H:%M:%S')

        if self.msg.message_type == b'A':
            ### LOGON
            self.next_seq_num = 1
            self.client_id = self.msg.get(simplefix.TAG_TARGET_COMPID)  #b'TARGED'
            self.target_id = self.msg.get(simplefix.TAG_SENDER_COMPID) #b'SENDER'
            values = {
                simplefix.TAG_SENDING_TIME: send_time_str,
                simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_LOGON,
                simplefix.TAG_ENCRYPTMETHOD: simplefix.ENCRYPTMETHOD_NONE,
                simplefix.TAG_HEARTBTINT: b'30',
                simplefix.TAG_RESETSEQNUMFLAG: simplefix.RESETSEQNUMFLAG_YES,
                **({}),
            }
        elif self.msg.message_type == b'D':
            # SELL
            self.client_id = self.msg.get(simplefix.TAG_TARGET_COMPID)
            self.target_id = self.msg.get(simplefix.TAG_SENDER_COMPID)
            values = {
                simplefix.TAG_SENDING_TIME: send_time_str,   ### flag 1

                simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_EXECUTION_REPORT,
                simplefix.TAG_HANDLINST: simplefix.HANDLINST_AUTO_PRIVATE,
                simplefix.TAG_CLORDID: uuid4(),
                simplefix.TAG_SYMBOL: self.msg.get(simplefix.TAG_SYMBOL),
                simplefix.TAG_SIDE: self.msg.get(simplefix.TAG_SIDE),
                simplefix.TAG_PRICE: self.msg.get(simplefix.TAG_PRICE),
                simplefix.TAG_ORDERQTY: self.msg.get(simplefix.TAG_ORDERQTY),
                simplefix.TAG_ORDTYPE: simplefix.ORDTYPE_LIMIT,
                simplefix.TAG_ORDSTATUS: simplefix.ORDSTATUS_FILLED,
                simplefix.TAG_EXECTYPE: simplefix.EXECTYPE_TRADE,
                simplefix.TAG_TIMEINFORCE: simplefix.TIMEINFORCE_GOOD_TILL_CANCEL,
                **({}),
            }
        elif self.msg.message_type == b'S':
            self.account = self.msg.get(simplefix.TAG_ACCOUNT) #запоминаем аккаунт для response
            xexcid = '654' #17 Идентификатор квазисделки
            symbol = "BTC/USDT" #55 Символьный идентификатор инструмента

            self.client_id = self.msg.get(simplefix.TAG_TARGET_COMPID)
            self.target_id = self.msg.get(simplefix.TAG_SENDER_COMPID)

            values = {
                simplefix.TAG_SENDING_TIME: send_time_str,   ### flag 1
                simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_NEW_ORDER_SINGLE,
                
                simplefix.TAG_CLORDID: uuid4(), #11 задается системой 
                simplefix.TAG_QUOTEREQID: self.msg.get(simplefix.TAG_QUOTEREQID), #131 из Quote
                simplefix.TAG_QUOTEID: self.msg.get(simplefix.TAG_QUOTEID), #117 из Quote
                simplefix.TAG_EXECID: xexcid,
                simplefix.TAG_SYMBOL: symbol,
                simplefix.TAG_PRICE: self.msg.get(simplefix.TAG_ASKBX), # 44<--133 из Quote
                simplefix.TAG_ORDTYPE: simplefix.ORDTYPE_LIMIT,
                simplefix.TAG_ORDERQTY: self.msg.get(b'135'), #38<--135  из Quote
                simplefix.TAG_SIDE: simplefix.SIDE_BUY,
                **({}),
            }

        elif rec == 1:

            symbol = "BTC/USDT"  # 55 Символьный идентификатор инструмента
            QuoteRespType = '1'

            self.client_id = self.msg.get(simplefix.TAG_TARGET_COMPID)
            self.target_id = self.msg.get(simplefix.TAG_SENDER_COMPID)

            values = {
                simplefix.TAG_SENDING_TIME: send_time_str,  ### flag 1
                simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_QUOTE_RESPONSE,

                simplefix.TAG_QUOTERESPID: self.QuoteRespID, #693
                simplefix.TAG_QUOTEREQID: self.msg.get(simplefix.TAG_QUOTEREQID), #131 из ExecutionRepor
                b'694': QuoteRespType, #694
                simplefix.TAG_SYMBOL: symbol,
                **({}),
            }

        elif self.msg.message_type == b'8': 
            self.QuoteRespID = uuid4()

            self.client_id = self.msg.get(simplefix.TAG_TARGET_COMPID)
            self.target_id = self.msg.get(simplefix.TAG_SENDER_COMPID)


            values = {
                simplefix.TAG_MSGTYPE: simplefix.MSGTYPE_EXECUTION_REPORT, #35=8
                simplefix.TAG_SENDING_TIME: send_time_str, #52

                simplefix.TAG_CLORDID: self.account, #1
                simplefix.TAG_QUOTERESPID: self.QuoteRespID,  # 693
                simplefix.TAG_EXECID: self.msg.get(simplefix.TAG_EXECID),  # 17 из report
                simplefix.TAG_ORDERID: self.msg.get(simplefix.TAG_CLORDID),  # 37 из report
                b'21002': self.msg.get(simplefix.TAG_QUOTEREQID), #21002<--131 из report
                simplefix.TAG_SYMBOL: self.msg.get(simplefix.TAG_SYMBOL),  # 55 из report
                simplefix.TAG_EXECTYPE: self.msg.get(simplefix.TAG_EXECTYPE),  # 150 из report
                simplefix.TAG_ORDSTATUS: self.msg.get(simplefix.TAG_ORDSTATUS),  # 39 из report
                simplefix.TAG_SIDE: simplefix.SIDE_SELL,  # 54 из report
                simplefix.TAG_PRICE: self.msg.get(simplefix.TAG_PRICE),  # 44 из report
                simplefix.TAG_AVGPX: self.msg.get(simplefix.TAG_AVGPX),  # 6 из report
                simplefix.TAG_CUMQTY: self.msg.get(simplefix.TAG_CUMQTY),  # 14 из report
                simplefix.TAG_LEAVESQTY: self.msg.get(simplefix.TAG_LEAVESQTY),  # 151 из report
                **({}),
            }

        else:
            self.next_seq_num = 1
            values = {
                **({}),
            }

        msg = FixMessage()
        msg.append_pair(simplefix.TAG_BEGINSTRING, 'FIX.4.4')
        msg.append_pair(simplefix.TAG_SENDER_COMPID, self.client_id)
        msg.append_pair(simplefix.TAG_TARGET_COMPID, self.target_id)
        msg.append_pair(simplefix.TAG_MSGSEQNUM, self.next_seq_num)
        # msg.append_utc_timestamp(simplefix.TAG_SENDING_TIME) ### flag 2

        for key, value in values.items():
            if isinstance(value, datetime.datetime):
                msg.append_utc_timestamp(key, value)
            else:
                msg.append_pair(key, value)

        self.encoded = msg.encode()
        self.next_seq_num = self.next_seq_num + 1
        return self.encoded

class FixEP(HTTPEndpoint):
    async def get(self, request):
        template = "fix.html"
        context = {"request": request}
        return templates.TemplateResponse(template, context)