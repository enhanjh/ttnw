from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    assets = relationship("Asset", back_populates="portfolio")
    transactions = relationship("Transaction", back_populates="portfolio")

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True) # Removed unique=True
    name = Column(String)
    asset_type = Column(String) # e.g., 'stock', 'bond', 'fund'
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))

    portfolio = relationship("Portfolio", back_populates="assets")
    transactions = relationship("Transaction", back_populates="asset")

    __table_args__ = (UniqueConstraint('symbol', 'portfolio_id', name='_symbol_portfolio_uc'),)

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    transaction_type = Column(String) # 'buy' or 'sell'
    quantity = Column(Float)
    price = Column(Float)
    fee = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    transaction_date = Column(DateTime(timezone=True), server_default=func.now())

    asset = relationship("Asset", back_populates="transactions")
    portfolio = relationship("Portfolio", back_populates="transactions")

class US_Symbol(Base):
    __tablename__ = "us_symbols"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    name = Column(String)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())

class KOSPI_Symbol(Base):
    __tablename__ = "kospi_symbols"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    name = Column(String)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())

class KOSDAQ_Symbol(Base):
    __tablename__ = "kosdaq_symbols"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    name = Column(String)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
