import os
from pathlib import Path
from dotenv import load_dotenv
from src.enums import EnvVariables


def init_environment():
    if os.getenv(EnvVariables.APP_ENVIRONMENT):
        return
    
    env_path = Path(__file__).resolve().parent.parent / EnvVariables.ENV_NAME
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        print("No environment variables found in OS, and no .env file at {env_path}")

init_environment()