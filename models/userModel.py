from sqlalchemy import Column, String, Integer
from models.dataBase import base

class Users(base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(64), nullable=False)
    password = Column(String(64), nullable=False)
    description = Column(String(256), nullable=False)