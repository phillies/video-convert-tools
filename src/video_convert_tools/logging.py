from loguru import logger
from rich.logging import RichHandler

# explicitly export the imported logger, so it can be used in other modules
__all__ = ["logger"]

logger.configure(handlers=[{"sink": RichHandler(), "format": "{message}"}])
