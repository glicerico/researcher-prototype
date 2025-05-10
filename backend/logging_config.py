import logging

def configure_logging(level=logging.INFO):
    """Configure global logging settings
    
    Args:
        level: The base logging level for application loggers
        
    Returns:
        The configured root logger
    """
    # Configure the basic logging format
    logging.basicConfig(
        level=level,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Set specific third-party loggers to WARNING to reduce noise
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("openai._base_client").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    
    # Get the root logger for the application
    app_logger = logging.getLogger("backend")
    app_logger.setLevel(level)
    
    # Return the configured logger
    return app_logger

def enable_debug_logging():
    """Enable debug logging for development troubleshooting
    
    This function can be called at runtime to increase log verbosity
    when needed for troubleshooting.
    """
    logging.getLogger("backend").setLevel(logging.DEBUG)
    logging.getLogger("backend.graph").setLevel(logging.DEBUG)
    print("Debug logging enabled for application loggers")

def get_logger(name):
    """Get a logger with the specified name
    
    Args:
        name: The name for the logger, typically __name__
        
    Returns:
        A configured logger instance
    """
    # For application modules, use a consistent prefix
    if not name.startswith("backend.") and not name == "backend":
        if name.startswith("__"):
            # Handle special case for __main__ etc.
            name = f"backend.{name}"
        else:
            name = f"backend.{name}"
    
    return logging.getLogger(name) 