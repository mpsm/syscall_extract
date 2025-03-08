import argparse


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract syscall information from Linux headers."
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Set logging level (default: info)",
    )
    parser.add_argument(
        "--gcc", default="gcc", help="Path to GCC binary (default: 'gcc')"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="syscalls.json",
        help="Output file path (default: 'syscalls.json')",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text", "header"],
        default="json",
        help="Output format (default: json)",
    )
    # Add libclang path option
    parser.add_argument(
        "--libclang-path",
        help="Path to libclang.so (optional, will try to find automatically if not specified)",
    )

    return parser.parse_args()
