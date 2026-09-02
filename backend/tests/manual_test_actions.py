import asyncio

from app.recovery.actions_repository import (
    ensure_indexes,
    create_requested_action,
    get_action,
)


async def main():
    await ensure_indexes()

    result = await create_requested_action(
        idempotency_key="test_action_001",
        case_id="case_test",
        action_type="send_payment_link",
        amount_paise=99900,
        approved_by="policy_engine:v1",
    )

    print("CREATED:", result)

    stored = await get_action(
        "test_action_001"
    )

    print("STORED:", stored)


if __name__ == "__main__":
    asyncio.run(main())