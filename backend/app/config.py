import os


class Settings:
    """
    Application configuration loaded from environment variables.
    """

    def __init__(self) -> None:
        self.mongo_uri = os.environ.get(
            "MONGO_URI",
            "mongodb://localhost:27017",
        )

        self.mongo_db_name = os.environ.get(
            "MONGO_DB_NAME",
            "recoup",
        )

        self.razorpay_key_id = os.environ.get(
            "RAZORPAY_KEY_ID",
            "",
        )

        self.razorpay_key_secret = os.environ.get(
            "RAZORPAY_KEY_SECRET",
            "",
        )

        self.razorpay_webhook_secret = os.environ.get(
            "RAZORPAY_WEBHOOK_SECRET",
            "",
        )

        self.llm_provider = os.environ.get(
            "LLM_PROVIDER",
            "anthropic",
        )

        self.llm_api_key = os.environ.get(
            "LLM_API_KEY",
            "",
        )

        self.llm_model = os.environ.get(
            "LLM_MODEL",
            "claude-sonnet-4-6",
        )

        self.recovery_max_retries = int(
            os.environ.get(
                "RECOVERY_MAX_RETRIES",
                "3",
            )
        )

        self.recovery_auto_approval_limit_paise = int(
            os.environ.get(
                "RECOVERY_AUTO_APPROVAL_LIMIT_PAISE",
                "500000",
            )
        )

        self.recovery_window_hours = int(
            os.environ.get(
                "RECOVERY_WINDOW_HOURS",
                "72",
            )
        )


settings = Settings()