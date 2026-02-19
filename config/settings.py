import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    BASE_URL: str = os.getenv("STRIPE_BASE_URL", "https://api.stripe.com/v1")
    API_KEY: str = os.getenv("STRIPE_TEST_SECRET_KEY", "")
    REQUEST_TIMEOUT: int = 30

    @classmethod
    def get_headers(cls) -> dict:
        return {
            "Authorization": f"Bearer {cls.API_KEY}",
        }

    @classmethod
    def validate(cls) -> None:
        if not cls.API_KEY:
            raise EnvironmentError(
                "STRIPE_TEST_SECRET_KEY is not set. "
                "Export it or add it to a .env file."
            )
        if not (cls.API_KEY.startswith("sk_test_") or cls.API_KEY.startswith("rk_test_")):
            raise EnvironmentError(
                "STRIPE_TEST_SECRET_KEY must start with 'sk_test_' or 'rk_test_'. "
                "Do not use a live key."
            )
