import logging
import sys
from typing import Optional

def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Configure global logging settings for the application.
    
    Args:
        level: The logging level to set (default: INFO)
        
    Returns:
        A logger instance for the application
    """
    # Create a root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create and configure console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s', 
        datefmt='%H:%M:%S'
    ))
    
    # Add the handler to the root logger
    root_logger.addHandler(console)
    
    # Set third-party loggers to WARNING to reduce noise
    for logger_name in ['httpx', 'urllib3', 'asyncio', 'openai', 'httpcore']:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # Return a logger for the main application
    return get_logger('backend')

def enable_debug_logging() -> None:
    """
    Enable debug logging for the application.
    This can be called during runtime to increase log verbosity.
    """
    # Set root logger and all handlers to DEBUG
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    for handler in root_logger.handlers:
        handler.setLevel(logging.DEBUG)
    
    # Log that debug mode has been enabled
    get_logger('backend').info("Debug logging enabled")

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: The name of the logger
        
    Returns:
        A logger instance
    """
    return logging.getLogger(name) 