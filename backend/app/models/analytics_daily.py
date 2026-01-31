from sqlalchemy import Column, Date, Integer, Text

from .base import Base


class AnalyticsDaily(Base):
    __tablename__ = "analytics_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    day = Column(Date, nullable=False, index=True)
    metrics = Column(Text, nullable=False)
