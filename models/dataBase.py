import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = sqlalchemy.create_engine('sqlite:///ChatDB.db') #регистрируем движок
sessionDB = sessionmaker(bind=engine)
base = declarative_base()

def createDB():
    base.metadata.create_all(engine)
