import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv()

def get_project_root() -> Path:
    """
    Get PROJECT_ROOT independantly from whether local machine or inside container
    
    - In container: Use $PROJECT_ROOT defined in docker-compose.yml
    - Locally: Looks for .env 
    """

    project_root_env = os.getenv('PROJECT_ROOT')
    if project_root_env:
        project_root = Path(project_root_env).resolve()
        return project_root


def get_project_name(env_name="PROJECT_NAME"):
    """
    Retrieves the path from the env_name environment variable.
    Allows the access to value in code, without the need of the env var name
    Returns:
        str: The value of the env_name environment variable.

    Raises:
        ValueError: If the env_name environment variable is not set or is empty.
    """
    env_value = os.getenv(env_name)
    if not env_value:
        raise ValueError(f"The {env_name} environment variable is not set or is empty.")
    return env_value



def get_var_from_env(env_name):
    """
    Retrieves the path from the env_name environment variable.
    Allows the access to value in code, without the need of the env var name
    Returns:
        str: The value of the env_name environment variable.

    Raises:
        ValueError: If the env_name environment variable is not set or is empty.
    """
    env_value = os.getenv(env_name)
    if not env_value:
        raise ValueError(f"The {env_name} environment variable is not set or is empty.")
    return env_value
