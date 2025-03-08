import logging


# Setup colored logging
class ColoredFormatter(logging.Formatter):
    """Colored log formatter with improved visual appearance."""

    COLORS = {
        # Log levels
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[41m\033[37m",  # White on Red background
        # Other elements
        "DATE": "\033[90m",  # Dark gray for timestamp
        "DELIMITER": "\033[36m",  # Cyan for delimiters
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record):
        # Format the message with the parent formatter
        formatted_msg = super().format(record)

        # Split the message to separate timestamp and the rest
        parts = formatted_msg.split(" - ", 1)

        if len(parts) == 2:
            timestamp, rest = parts
            level_name = record.levelname

            # Add timestamp with its own color
            date_colored = f"{self.COLORS['DATE']}{timestamp}{self.COLORS['RESET']}"

            # Add delimiter with its own color
            delimiter = f"{self.COLORS['DELIMITER']} - {self.COLORS['RESET']}"

            # Add level name with appropriate color and fixed width for alignment
            if level_name in self.COLORS:
                level_colored = (
                    f"{self.COLORS[level_name]}{level_name:8}{self.COLORS['RESET']}"
                )

                # Extract the message part (after level name)
                msg_parts = rest.split(" - ", 1)
                if len(msg_parts) > 1:
                    message = msg_parts[1]
                    # Reconstruct with colors and alignment
                    return f"{date_colored}{delimiter}{level_colored} - {message}"

        # Fallback to original coloring if parsing fails
        level_name = record.levelname
        if level_name in self.COLORS:
            return f"{self.COLORS[level_name]}{formatted_msg}{self.COLORS['RESET']}"
        return formatted_msg


def setup_logging(level: str) -> None:
    """Set up logging with the specified level and colored output."""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    logger = logging.getLogger()
    logger.setLevel(numeric_level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setLevel(numeric_level)

    formatter = ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
