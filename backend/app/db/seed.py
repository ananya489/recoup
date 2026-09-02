import asyncio

from app.db.mongo import get_db


async def seed():
    db = get_db()

    print("Connecting to MongoDB...")

    await db.customers.delete_many({})
    await db.payments.delete_many({})
    await db.recovery_cases.delete_many({})

    await db.customers.insert_one({
        "_id": "cust_00042",
        "name": "Rohan Mehra",
        "email": "rohan@example.com",
        "contact": "+919900011122",
        "account_age_days": 240,
        "ltv_paise": 899100,
        "prior_failures_90d": 1,
        "prior_chargebacks": 0,
        "segment": "d2c_subscription",
    })

    await db.payments.insert_one({
        "_id": "pay_QaBc12345",
        "razorpay_order_id": "order_QaBc999",
        "customer_id": "cust_00042",
        "amount_paise": 99900,
        "currency": "INR",
        "method": "upi",
        "status": "failed",
        "error_code": "BAD_REQUEST_ERROR",
        "error_description": (
            "Your payment could not be completed due to "
            "insufficient balance."
        ),
    })

    await db.recovery_cases.insert_one({
        "_id": "case_7f3a",
        "payment_id": "pay_QaBc12345",
        "customer_id": "cust_00042",
        "amount_paise": 99900,
        "status": "open",
        "auto_retry_count": 0,
    })

    print("Seed complete.")
    print(
        "customers:",
        await db.customers.count_documents({})
    )
    print(
        "payments:",
        await db.payments.count_documents({})
    )
    print(
        "recovery_cases:",
        await db.recovery_cases.count_documents({})
    )


if __name__ == "__main__":
    asyncio.run(seed())