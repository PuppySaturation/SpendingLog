from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Expense(Base):
    __tablename__ = 'expenses'

    id = Column(Integer, primary_key=True)
    item_name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    date = Column(Date, nullable=False)

    labels = relationship('Label', secondary='expense_labels', backref='expenses')

class Label(Base):
    __tablename__ = 'labels'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)

class ExpenseLabel(Base):
    __tablename__ = 'expense_labels'

    expense_id = Column(Integer, ForeignKey('expenses.id'), primary_key=True)
    label_id = Column(Integer, ForeignKey('labels.id'), primary_key=True)
