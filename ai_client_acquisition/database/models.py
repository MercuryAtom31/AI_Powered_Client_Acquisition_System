from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()

class PlatformType(enum.Enum):
    WORDPRESS = "wordpress"
    SHOPIFY = "shopify"
    CUSTOM = "custom"
    UNKNOWN = "unknown"

class OutreachStatus(enum.Enum):
    NOT_CONTACTED = "not_contacted"
    PITCHED = "pitched"
    REPLIED = "replied"
    LANDED = "landed"
    REJECTED = "rejected"

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    website_url = Column(String, unique=True, nullable=False)
    platform_type = Column(Enum(PlatformType), nullable=False)
    company_name = Column(String)
    industry = Column(String)
    discovery_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contact_info = relationship("ContactInfo", back_populates="company", uselist=False)
    seo_analysis = relationship("SEOAnalysis", back_populates="company", uselist=False)
    outreach_history = relationship("OutreachHistory", back_populates="company")

class ContactInfo(Base):
    __tablename__ = "contact_info"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    email = Column(String)
    phone = Column(String)
    social_media = Column(JSON)  # Store as JSON: {"linkedin": "url", "twitter": "url", etc.}
    contact_page_url = Column(String)
    last_verified = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="contact_info")

class SEOAnalysis(Base):
    __tablename__ = "seo_analysis"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    title_tag = Column(String)
    meta_description = Column(String)
    header_structure = Column(JSON)  # Store as JSON: {"h1": ["text1", "text2"], "h2": [...], etc.}
    keywords = Column(JSON)  # Store as JSON: {"primary": ["kw1", "kw2"], "secondary": [...]}
    internal_links = Column(Integer)
    external_links = Column(Integer)
    images_without_alt = Column(Integer)
    analysis_date = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="seo_analysis")

class OutreachHistory(Base):
    __tablename__ = "outreach_history"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    status = Column(Enum(OutreachStatus), nullable=False)
    email_content = Column(String)
    sent_date = Column(DateTime, default=datetime.utcnow)
    reply_date = Column(DateTime)
    reply_content = Column(String)
    notes = Column(String)

    # Relationships
    company = relationship("Company", back_populates="outreach_history") 