import logging
import subprocess
from typing import List, Optional


def expand_macros(header_name: str, gcc_bin: str) -> Optional[str]:
    """Extract macro definitions from header file using gcc -E -dM."""
    logging.debug(f"Extracting macros from header: {header_name}")

    try:
        logging.debug(
            f"Running command: {gcc_bin} -E -dM -include {header_name} - </dev/null"
        )

        # Use -include flag with -dM to get only macro definitions
        expanded = subprocess.check_output(
            [gcc_bin, "-E", "-dM", "-include", header_name, "-"],
            input="",
            universal_newlines=True,
            stderr=subprocess.DEVNULL,  # Suppress warnings about deprecated features
        )

        lines = expanded.count("\n")
        logging.debug(f"Extracted {lines} macro definitions")

        return expanded
    except subprocess.CalledProcessError as e:
        logging.error(f"Error processing header {header_name}: {e}")
        return None


def expand(header_name: str, gcc_bin: str) -> Optional[str]:
    """Extract macro definitions from header file using gcc"""
    logging.debug(f"Extracting macros from header: {header_name}")

    try:
        cmdname = gcc_bin + " -E -P -include " + header_name + " - </dev/null"
        logging.debug(f"Running command: {cmdname}")
        expanded = subprocess.check_output(
            [gcc_bin, "-E", "-P", "-include", header_name, "-"],
            input="",
            universal_newlines=True,
            stderr=subprocess.DEVNULL,  # Suppress warnings about deprecated features
        )
    except subprocess.CalledProcessError as e:
        logging.error(f"Error processing header {header_name}: {e}")
        return None

    return expanded


def find_header_files(gcc: str, headers_list: List[str]) -> List[str]:
    """Find header files in the system include paths."""
    logging.info("Finding headers in system include paths")
    header_files = []

    for header in headers_list:
        logging.debug(f"Searching for header: {header}")
        if expand_macros(header, gcc) is None:
            logging.debug(f"Header not found: {header}")
            continue
        logging.info(f"Found header: {header}")
        header_files.append(header)

    return header_files
