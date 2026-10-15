from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from db.database import Base


class Product(Base):
    """
    One row per unique product URL.
    Same product on Amazon and Flipkart = two rows (different platforms).
    """
    __tablename__ = "products"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(500), nullable=False)
    platform      = Column(String(50),  nullable=False)   # "amazon" | "flipkart"
    url           = Column(Text,        nullable=False, unique=True)
    image_url     = Column(Text,        nullable=True)
    description   = Column(Text,        nullable=True)    # spec bullets from detail page
    search_query  = Column(String(255), nullable=True)    # what was searched
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    price_records = relationship("PriceRecord", back_populates="product",
                                 cascade="all, delete-orphan")
    alerts        = relationship("PriceAlert",  back_populates="product",
                                 cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product {self.platform} | {self.name[:40]}>"


class PriceRecord(Base):
    """
    Every scrape saves one row here.
    This is the time-series data that Prophet trains on.
    """
    __tablename__ = "price_records"

    id         = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    price      = Column(Float,   nullable=False)
    scraped_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    product    = relationship("Product", back_populates="price_records")

    def __repr__(self):
        return f"<PriceRecord ₹{self.price} @ {self.scraped_at}>"


class PriceAlert(Base):
    """
    User sets a target price. Celery checks hourly and emails when hit.
    """
    __tablename__ = "price_alerts"

    id           = Column(Integer, primary_key=True, index=True)
    product_id   = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    target_price = Column(Float,   nullable=False)
    email        = Column(String(255), nullable=False)
    is_active    = Column(Boolean, default=True)
    triggered_at = Column(DateTime, nullable=True)   # set when alert fires
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    product      = relationship("Product", back_populates="alerts")

    def __repr__(self):
        return f"<PriceAlert ₹{self.target_price} → {self.email}>"