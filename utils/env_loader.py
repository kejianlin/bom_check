from pathlib import Path

from dotenv import load_dotenv


def load_project_env() -> Path:
    """
    Load the project root .env explicitly instead of relying on current
    working directory. This keeps Windows service/NSSM startup behavior
    consistent with manual startup.
    """
    project_root = Path(__file__).resolve().parent.parent
    dotenv_path = project_root / ".env"
    load_dotenv(dotenv_path=dotenv_path)
    return dotenv_path
