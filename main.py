import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product as ProductSchema, Order as OrderSchema, Testimonial as TestimonialSchema, ContactMessage as ContactSchema

app = FastAPI(title="Nasir Store API", description="E-commerce API for selling premium app accounts")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Nasir Store Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["connection_status"] = "Connected"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, "name") else ("✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set")
            try:
                response["collections"] = db.list_collection_names()
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but error: {str(e)[:100]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:100]}"
    return response


# -------------------- Utility --------------------

def to_dict(doc):
    if not doc:
        return doc
    doc["_id"] = str(doc.get("_id"))
    return doc


# -------------------- Products --------------------

class ProductCreate(ProductSchema):
    pass

@app.get("/api/products")
def list_products(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None),
    featured: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=200),
):
    filt = {"is_active": True}
    if category:
        filt["category"] = category
    if featured is not None:
        filt["is_featured"] = featured
    if q:
        # Basic search across fields
        filt["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"short_description": {"$regex": q, "$options": "i"}},
        ]
    docs = db["product"].find(filt).limit(limit)
    return [to_dict(d) for d in docs]


@app.get("/api/products/{slug}")
def get_product(slug: str):
    doc = db["product"].find_one({"slug": slug, "is_active": True})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return to_dict(doc)


@app.post("/api/seed")
def seed_products():
    # Seed only if empty
    count = db["product"].count_documents({})
    if count > 0:
        return {"seeded": False, "message": "Products already exist"}
    samples: List[ProductCreate] = [
        ProductCreate(
            name="Netflix Premium",
            slug="netflix-premium",
            description="Akun Netflix Premium kualitas 4K. Garansi sesuai ketentuan. Metode login: Shared Profile.",
            short_description="Netflix 4K, garansi, hemat.",
            logo_url="https://upload.wikimedia.org/wikipedia/commons/0/08/Netflix_2015_logo.svg",
            category="Streaming",
            durations=["1 Month", "3 Months", "12 Months"],
            login_method="Shared",
            price_monthly=35000,
            price_lifetime=None,
            is_featured=True,
            is_active=True,
        ),
        ProductCreate(
            name="Spotify Premium",
            slug="spotify-premium",
            description="Spotify Premium no ads, kualitas tinggi. Metode login: Invite Family/Shared.",
            short_description="Musik bebas iklan.",
            logo_url="https://upload.wikimedia.org/wikipedia/commons/1/19/Spotify_logo_without_text.svg",
            category="Music",
            durations=["1 Month", "3 Months", "12 Months"],
            login_method="Shared",
            price_monthly=15000,
            is_featured=True,
            is_active=True,
            price_lifetime=None,
        ),
        ProductCreate(
            name="Canva Pro",
            slug="canva-pro",
            description="Canva Pro fitur lengkap. Metode login: Invite ke team.",
            short_description="Desain tanpa batas.",
            logo_url="https://upload.wikimedia.org/wikipedia/commons/a/af/Canva_icon_2021.svg",
            category="Design",
            durations=["1 Month", "3 Months", "12 Months"],
            login_method="Invite",
            price_monthly=20000,
            is_featured=True,
            is_active=True,
        ),
        ProductCreate(
            name="ChatGPT Plus",
            slug="chatgpt-plus",
            description="Akses GPT-4/Plus sesuai ketentuan penyedia. Metode: Shared.",
            short_description="AI asisten premium.",
            logo_url="https://upload.wikimedia.org/wikipedia/commons/0/04/ChatGPT_logo.svg",
            category="AI",
            durations=["1 Month", "3 Months"],
            login_method="Shared",
            price_monthly=120000,
            is_featured=False,
            is_active=True,
        ),
        ProductCreate(
            name="YouTube Premium",
            slug="youtube-premium",
            description="YouTube Premium bebas iklan. Metode: Invite Family.",
            short_description="Streaming tanpa iklan.",
            logo_url="https://upload.wikimedia.org/wikipedia/commons/e/ef/Youtube_logo.png",
            category="Streaming",
            durations=["1 Month", "3 Months", "12 Months"],
            login_method="Invite",
            price_monthly=20000,
            is_featured=False,
            is_active=True,
        ),
    ]
    for p in samples:
        create_document("product", p)
    return {"seeded": True, "count": len(samples)}


# -------------------- Orders & Payments --------------------

class OrderCreate(BaseModel):
    product_slug: str
    package: str
    buyer_name: str
    email: str
    whatsapp: str
    payment_method: str  # "QRIS" | "Bank Transfer" | "E-Wallet"
    delivery_channel: str = "email"  # email | whatsapp | both


def generate_order_code() -> str:
    return f"NS-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


@app.post("/api/orders")
def create_order(payload: OrderCreate):
    product = db["product"].find_one({"slug": payload.product_slug})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    # Determine price from package
    base = product.get("price_monthly", 0)
    multiplier = {
        "1 Month": 1,
        "3 Months": 3,
        "6 Months": 6,
        "12 Months": 12,
        "Lifetime": 20,  # arbitrary demo multiplier
    }.get(payload.package)
    if multiplier is None:
        raise HTTPException(status_code=400, detail="Invalid package")
    price = float(base) * float(multiplier)
    order_code = generate_order_code()

    order = OrderSchema(
        product_id=str(product.get("_id")),
        product_name=product.get("name"),
        package=payload.package,
        price=price,
        buyer_name=payload.buyer_name,
        email=payload.email,
        whatsapp=payload.whatsapp,
        payment_method=payload.payment_method,
        status="pending",
        order_code=order_code,
        delivery_channel=payload.delivery_channel,
    )
    inserted_id = create_document("order", order)

    # Return mock payment instruction (for demo only)
    payment_instructions = {
        "QRIS": {
            "type": "qris",
            "note": "Scan QR berikut di aplikasi e-wallet Anda",
            "qr_image": "https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=NASIR-STORE-DEMO",
        },
        "Bank Transfer": {
            "type": "bank",
            "bank": "BCA",
            "account_name": "NASIR STORE",
            "account_number": "1234567890",
        },
        "E-Wallet": {
            "type": "ewallet",
            "provider": "OVO/DANA/GoPay",
            "number": "0812-3456-7890",
            "name": "NASIR STORE",
        },
    }.get(payload.payment_method, {"type": "info", "note": "Follow admin instruction"})

    return {
        "order_id": inserted_id,
        "order_code": order_code,
        "status": "pending",
        "amount": price,
        "product_name": product.get("name"),
        "package": payload.package,
        "payment": payment_instructions,
    }


@app.get("/api/orders/{order_code}")
def get_order(order_code: str):
    doc = db["order"].find_one({"order_code": order_code})
    if not doc:
        raise HTTPException(status_code=404, detail="Order not found")
    return to_dict(doc)


class PaymentNotify(BaseModel):
    order_code: str
    status: str  # "paid" or "failed"


@app.post("/api/payments/notify")
def payment_notify(payload: PaymentNotify):
    order = db["order"].find_one({"order_code": payload.order_code})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    new_status = "paid" if payload.status == "paid" else "failed"
    delivery_payload = None

    if new_status == "paid":
        # Simulate instant delivery with demo credentials
        delivery_payload = {
            "username": f"demo_{payload.order_code.lower()}@nasirstore.io",
            "password": "AutoGenerated123!",
            "note": "Gunakan kredensial ini sesuai ketentuan. Ini demo.",
        }
        db["order"].update_one(
            {"_id": order["_id"]},
            {"$set": {"status": "delivered", "delivered_payload": delivery_payload, "updated_at": datetime.utcnow()}},
        )
        return {"updated": True, "status": "delivered", "delivered_payload": delivery_payload}
    else:
        db["order"].update_one(
            {"_id": order["_id"]},
            {"$set": {"status": new_status, "updated_at": datetime.utcnow()}},
        )
        return {"updated": True, "status": new_status}


# -------------------- Testimonials --------------------

@app.get("/api/testimonials")
def list_testimonials(limit: int = 50):
    docs = db["testimonial"].find({}).sort("created_at", -1).limit(limit)
    return [to_dict(d) for d in docs]


@app.post("/api/testimonials")
def create_testimonial(body: TestimonialSchema):
    inserted_id = create_document("testimonial", body)
    return {"inserted_id": inserted_id}


# -------------------- Contact --------------------

@app.post("/api/contact")
def create_contact(body: ContactSchema):
    inserted_id = create_document("contactmessage", body)
    return {"inserted_id": inserted_id}


# -------------------- Schema Endpoint --------------------

@app.get("/schema")
def get_schema_info():
    return {
        "collections": ["product", "order", "testimonial", "contactmessage"],
        "docs": "Models are defined in schemas.py as Pydantic models.",
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
