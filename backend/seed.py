"""Seed database with demo users, capabilities, and products."""

from decimal import Decimal

from app.auth.passwords import hash_password
from app.capabilities import ALL_CAPABILITIES, EMAIL_SEND, INVENTORY_READ, ORDER_CREATE, POLICY_READ
from app.db.session import SessionLocal, init_db
from app.models.product import Product
from app.models.user import User, UserCapability

DEMO_PASSWORD = "DemoPass123!"

PRODUCTS = [
    ("SKU-1001", "A4 Copy Paper", 450, "6.50", "OfficeHub"),
    ("SKU-1002", "Blue Ballpoint Pens", 18, "0.80", "PenCo"),
    ("SKU-1003", "Black Ballpoint Pens", 220, "0.80", "PenCo"),
    ("SKU-1004", "Staplers", 9, "12.00", "OfficeHub"),
    ("SKU-1005", "Staples Box", 75, "2.40", "OfficeHub"),
    ("SKU-1006", "Desk Notebooks", 14, "5.25", "PaperWorks"),
    ("SKU-1007", "Shipping Labels", 310, "9.90", "PackRight"),
    ("SKU-1008", "USB-C Cables", 7, "8.75", "TechSource"),
    ("SKU-1009", "Wireless Keyboards", 42, "24.00", "TechSource"),
    ("SKU-1010", "Wireless Mice", 36, "18.00", "TechSource"),
    ("SKU-1011", "Packing Tape", 11, "4.60", "PackRight"),
    ("SKU-1012", "Cardboard Boxes M", 160, "1.90", "PackRight"),
    ("SKU-1013", "Whiteboard Markers", 64, "6.80", "OfficeHub"),
    ("SKU-1014", "Printer Toner Black", 5, "89.00", "PrintSupply"),
    ("SKU-1043", "Thermal Receipt Rolls", 120, "15.00", "RetailPrint"),
]

USER_SPECS = [
    ("ali@assistant.test", [POLICY_READ, INVENTORY_READ], False),
    ("sara@assistant.test", [POLICY_READ, INVENTORY_READ, ORDER_CREATE], False),
    ("admin@assistant.test", list(ALL_CAPABILITIES), True),
    ("dave@assistant.test", [], False),
]


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        pwd = hash_password(DEMO_PASSWORD)
        for email, caps, is_admin in USER_SPECS:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(email=email, password_hash=pwd, is_admin=is_admin, is_active=True)
                db.add(user)
                db.flush()
            else:
                user.password_hash = pwd
                user.is_admin = is_admin
                user.is_active = True
            db.query(UserCapability).filter(UserCapability.user_id == user.id).delete()
            for cap in caps:
                db.add(UserCapability(user_id=user.id, capability=cap))
        for sku, name, qty, price, supplier in PRODUCTS:
            existing = db.query(Product).filter(Product.sku == sku).first()
            if existing:
                existing.name = name
                existing.quantity = qty
                existing.price = Decimal(price)
                existing.supplier = supplier
            else:
                db.add(
                    Product(
                        sku=sku,
                        name=name,
                        quantity=qty,
                        price=Decimal(price),
                        supplier=supplier,
                    )
                )
        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
