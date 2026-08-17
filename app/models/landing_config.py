import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, JSON, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def generate_config_id() -> str:
    return f"lpc-{uuid.uuid4().hex[:8]}"


class LandingPageConfig(Base):
    __tablename__ = "landing_page_config"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        default="landing-config-current",
        index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Structured JSON configuration for Landing Page
    brand: Mapped[dict] = mapped_column(JSON, nullable=False)
    nav: Mapped[list] = mapped_column(JSON, nullable=False)
    hero: Mapped[dict] = mapped_column(JSON, nullable=False)
    features: Mapped[list] = mapped_column(JSON, nullable=False)
    solutions: Mapped[list] = mapped_column(JSON, nullable=False)
    pricing_plans: Mapped[list] = mapped_column(JSON, nullable=False)
    testimonials: Mapped[list] = mapped_column(JSON, nullable=False)
    faqs: Mapped[list] = mapped_column(JSON, nullable=False)
    footer: Mapped[dict] = mapped_column(JSON, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_by: Mapped[str] = mapped_column(String(50), nullable=True)
