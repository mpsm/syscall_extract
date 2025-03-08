#!/usr/bin/env python3

import sys
import logging
import os

# Ensure the src directory is in the path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "extract-syscalls", "src")
sys.path.append(src_dir)

# Import modules
from .logging_utils import setup_logging
from .cli import parse_arguments
from .libclang_utils import check_libclang_path
from .syscall_extractor import extract_syscalls, SYSTEM_HEADERS
from .output_formatter import (
    format_output_json,
    format_output_text,
    format_output_header,
    write_output,
)


def main():
    """Main function to orchestrate the syscall extraction process."""
    args = parse_arguments()

    # Set up logging
    setup_logging(args.log_level)

    logging.info("Starting syscall extraction")
    logging.info(f"Using GCC: {args.gcc}")

    check_libclang_path(args)

    try:
        syscalls_ctx = extract_syscalls(args)
    except RuntimeError as e:
        logging.fatal("Failed to extract syscall definitions")
        sys.exit(1)

    logging.info(f"Found {len(syscalls_ctx.syscalls)} syscall definitions")

    # Log information about the extracted syscalls
    for _, syscall in sorted(syscalls_ctx.syscalls.items()):
        func_info = (
            f"with function definition"
            if syscall.function
            else "without function definition"
        )
        logging.debug(f"Syscall {syscall.name} (#{syscall.number}): {func_info}")
        if syscall.function:
            logging.debug(f"  - Return type: {syscall.function.return_type}")
            logging.debug(f"  - Arguments: {len(syscall.function.arguments)}")

    # Format output based on requested format
    if args.format == "json":
        output_content = format_output_json(syscalls_ctx)
    elif args.format == "text":
        output_content = format_output_text(syscalls_ctx)
    elif args.format == "header":
        output_content = format_output_header(syscalls_ctx)
    else:
        logging.fatal(f"Unsupported output format: {args.format}")
        sys.exit(1)

    # Write to output file with appropriate extension
    write_output(output_content, args.output, args.format)

    # Summary
    logging.info("Successfully processed syscall definitions")


if __name__ == "__main__":
    main()
