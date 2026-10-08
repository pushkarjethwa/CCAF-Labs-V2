"""Configuration. Secrets come from environment variables, never from source."""
import os


def get_api_key():
    """Return the rewards API key from the environment, or None when it is not set."""
    return os.environ.get("REWARDS_API_KEY")
