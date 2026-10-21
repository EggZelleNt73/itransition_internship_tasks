from pathlib import Path
from dotenv import load_dotenv
from src.enums import EnvVariables


def load_configs():
    ENV_PATH = Path(__file__).resolve().parent.parent / EnvVariables.ENV_NAME
    load_dotenv(dotenv_path=ENV_PATH)


if __name__ == "__main__":
    load_configs()