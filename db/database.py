from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    product_name = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    color = Column(String, nullable=False)
    category = Column(String, nullable=False)
    specifications = Column(Text, nullable=True)
    source = Column(String, nullable=False)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)

DATABASE_URL = "sqlite:///products.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    create_tables()
