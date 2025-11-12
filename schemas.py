"""
Database Schemas for Nasir Store

Each Pydantic model represents a MongoDB collection. The collection
name is the lowercase of the class name (e.g., Product -> "product").
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl, EmailStr

# Product sold in the store (e.g., Netflix, Spotify, Canva Pro, etc.)
class Product(BaseModel):
    name: str = Field(..., description="Product name, e.g., Netflix Premium")
    slug: str = Field(..., description="URL-friendly unique slug, e.g., netflix-premium")
    description: str = Field(..., description="Long description with features/terms")
    short_description: str = Field(..., description="Short teaser shown in cards")
    logo_url: Optional[HttpUrl] = Field(None, description="Logo or image URL")
    category: Literal[
        "Streaming",
        "Music",
        "Design",
        "AI",
        "Productivity",
        "Education",
        "Other",
    ] = Field("Other")
    durations: List[Literal["1 Month", "3 Months", "6 Months", "12 Months", "Lifetime"]] = Field(
        default_factory=lambda: ["1 Month", "3 Months", "12 Months"]
    )
    login_method: Literal["Shared", "Private", "Invite", "Redeem Code"] = Field("Shared")
    price_monthly: float = Field(..., ge=0, description="Base monthly price in IDR")
    price_lifetime: Optional[float] = Field(None, ge=0, description="Lifetime price if available")
    is_featured: bool = Field(False)
    is_active: bool = Field(True)

# Customer order
class Order(BaseModel):
    product_id: str = Field(..., description="Reference to product _id as string")
    product_name: str
    package: Literal["1 Month", "3 Months", "6 Months", "12 Months", "Lifetime"]
    price: float = Field(..., ge=0)
    buyer_name: str
    email: EmailStr
    whatsapp: str
    payment_method: Literal["QRIS", "Bank Transfer", "E-Wallet"]
    status: Literal["pending", "paid", "delivered", "failed"] = "pending"
    order_code: Optional[str] = None
    delivery_channel: Literal["email", "whatsapp", "both"] = "email"
    delivery_note: Optional[str] = None
    delivered_payload: Optional[dict] = None

# Testimonial / review
class Testimonial(BaseModel):
    name: str
    rating: int = Field(..., ge=1, le=5)
    comment: str
    product_slug: Optional[str] = None

# Contact form submissions
class ContactMessage(BaseModel):
    name: str
    email: EmailStr
    whatsapp: Optional[str] = None
    message: str

