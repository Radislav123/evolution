import os
from pathlib import Path


PROJECT_ROOT_PATH = Path(os.path.dirname(os.path.abspath(__file__)))

LOGS_PATH = f"{PROJECT_ROOT_PATH}/logs"

# изображения, звуки...
RESOURCES_PATH = f"{PROJECT_ROOT_PATH}/resources"
IMAGES_PATH = f"{RESOURCES_PATH}/images"
