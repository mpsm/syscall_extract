import json
import logging
import os
from collections import defaultdict

from .dataclass_serialization import DataclassJSONEncoder, dataclass_to_dict
from .model import SyscallsContext


def format_output_json(syscalls_ctx: SyscallsContext) -> str:
    """Format syscalls and typedefs as JSON."""
    logging.info("Formatting syscalls and typedefs as JSON")

    # Convert to list format under a "syscalls" element
    syscall_list = [
        dataclass_to_dict(syscall)
        for _, syscall in sorted(syscalls_ctx.syscalls.items())
    ]

    # Convert typedefs to list format
    typedef_list = [dataclass_to_dict(typedef) for typedef in syscalls_ctx.typedefs]

    # Convert type_store to a dictionary for the JSON output
    types_dict = {}
    if syscalls_ctx.type_store:
        for type_name, type_info in syscalls_ctx.type_store.items():
            types_dict[type_name] = dataclass_to_dict(type_info)
        logging.info(f"Adding {len(types_dict)} type definitions to JSON output")

    # Construct the full output dictionary with the new types section
    output_dict = {
        "syscalls": syscall_list,
        "typedefs": typedef_list,
        "types": types_dict,
    }

    return json.dumps(output_dict, cls=DataclassJSONEncoder, indent=2)


def format_output_text(syscalls_ctx: SyscallsContext) -> str:
    """Format syscalls and typedefs as structured plain text with ASCII tables."""
    logging.info("Formatting syscalls and typedefs as structured text")

    lines = ["SYSCALL DEFINITIONS", ""]

    # Group syscalls by header
    syscalls_by_header = defaultdict(list)
    for number, syscall in sorted(syscalls_ctx.syscalls.items()):
        syscalls_by_header[syscall.header_name].append(syscall)

    # For each header, create a well-formatted ASCII table
    for header, header_syscalls in sorted(syscalls_by_header.items()):
        lines.append(f"{header} ({len(header_syscalls)} syscalls)")
        lines.append("=" * len(f"{header} ({len(header_syscalls)} syscalls)"))
        lines.append("")

        # Prepare data for table
        table_data = []
        headers = ["Number", "Name", "Function Signature"]

        # Get function info for each syscall
        for syscall in sorted(header_syscalls, key=lambda s: s.number):
            function_info = "N/A"
            if syscall.function:
                args_str = ", ".join(
                    f"{arg.type} {arg.name}" if arg.name else arg.type
                    for arg in syscall.function.arguments
                )
                function_info = f"{syscall.function.return_type} {syscall.function.name}({args_str})"

            table_data.append([str(syscall.number), syscall.name, function_info])

        # Calculate column widths (add padding)
        col_widths = [len(headers[i]) for i in range(len(headers))]
        for row in table_data:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(cell))

        # Add some padding
        col_widths = [width + 2 for width in col_widths]

        # Create top border
        lines.append("+" + "+".join("-" * width for width in col_widths) + "+")

        # Create header row
        header_row = "|" + "".join(
            f" {headers[i]:{col_widths[i]-2}} |" for i in range(len(headers))
        )
        lines.append(header_row)

        # Create header-data separator
        lines.append("+" + "+".join("=" * width for width in col_widths) + "+")

        # Create data rows
        for row in table_data:
            data_row = "|" + "".join(
                f" {row[i]:{col_widths[i]-2}} |" for i in range(len(row))
            )
            lines.append(data_row)

        # Create bottom border
        lines.append("+" + "+".join("-" * width for width in col_widths) + "+")
        lines.append("")

    # Add typedefs section
    if syscalls_ctx.typedefs:
        lines.append("\nTYPEDEF DEFINITIONS")
        lines.append("===================\n")

        # Prepare data for typedef table
        typedef_data = []
        typedef_headers = ["Name", "Underlying Type"]

        for typedef in sorted(syscalls_ctx.typedefs, key=lambda t: t.name):
            typedef_data.append([typedef.name, typedef.underlying_type])

        # Calculate column widths
        col_widths = [len(typedef_headers[i]) for i in range(len(typedef_headers))]
        for row in typedef_data:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(cell))

        # Add padding
        col_widths = [width + 2 for width in col_widths]

        # Create top border
        lines.append("+" + "+".join("-" * width for width in col_widths) + "+")

        # Create header row
        header_row = "|" + "".join(
            f" {typedef_headers[i]:{col_widths[i]-2}} |"
            for i in range(len(typedef_headers))
        )
        lines.append(header_row)

        # Create header-data separator
        lines.append("+" + "+".join("=" * width for width in col_widths) + "+")

        # Create data rows
        for row in typedef_data:
            data_row = "|" + "".join(
                f" {row[i]:{col_widths[i]-2}} |" for i in range(len(row))
            )
            lines.append(data_row)

        # Create bottom border
        lines.append("+" + "+".join("-" * width for width in col_widths) + "+")
        lines.append("")

    return "\n".join(lines)


def format_output_header(syscalls_ctx: SyscallsContext) -> str:
    """Format syscalls and typedefs as a C header file."""
    logging.info("Formatting syscalls and typedefs as a C header")

    lines = [
        "/* Automatically generated syscall definitions */",
        "#ifndef _SYSCALL_NUMBERS_H",
        "#define _SYSCALL_NUMBERS_H",
        "",
        "#ifdef __cplusplus",
        'extern "C" {',
        "#endif",
        ""
        "#ifndef restrict",
        "#define restrict __restrict",
        "#endif",
        "",
    ]

    # Add typedefs
    if syscalls_ctx.typedefs:
        lines.append("/* Type definitions */")
        for typedef in sorted(syscalls_ctx.typedefs, key=lambda t: t.name):
            if "(" in typedef.underlying_type or "[" in typedef.underlying_type:
                # Output function pointers and arrays as comments
                lines.append(f"/* typedef {typedef.underlying_type} {typedef.name}; */")
                continue
            lines.append(f"typedef {typedef.underlying_type} {typedef.name};")
        lines.append("")

    lines.append("/* Syscall definitions */")

    for number, syscall in sorted(syscalls_ctx.syscalls.items()):
        lines.append(f"#define SYS_{syscall.name} {syscall.number}")

    lines.extend(
        [
            "",
            "/* Syscall function prototypes */",
        ]
    )

    for number, syscall in sorted(syscalls_ctx.syscalls.items()):
        if syscall.function:
            args_str = ", ".join(
                f"{syscalls_ctx.type_store[arg.type].to_argument_name(arg.name)}"
                for arg in syscall.function.arguments
            )
            lines.append(
                f"{syscall.function.return_type} {syscall.function.name}({args_str});"
            )
        else:
            # Add a comment for syscalls without a function definition
            lines.append(
                f"/* syscall {syscall.name} (#{syscall.number}) - no function definition available */"
            )

    lines.extend(
        [
            "",
            "#ifdef __cplusplus",
            "}",
            "#endif",
            "",
            "#endif /* _SYSCALL_NUMBERS_H */",
        ]
    )

    return "\n".join(lines)


def write_output(content: str, output_path: str, format_type: str) -> None:
    """Write content to output file or stdout with appropriate extension."""
    if output_path == "-":
        print(content)
        logging.info("Wrote output to stdout")
    else:
        # Change extension based on format type
        if "." in os.path.basename(output_path):
            # Remove existing extension if present
            output_path = os.path.splitext(output_path)[0]

        # Add appropriate extension
        if format_type == "json":
            output_path += ".json"
        elif format_type == "text":
            output_path += ".txt"
        elif format_type == "header":
            output_path += ".h"

        with open(output_path, "w") as f:
            f.write(content)
        logging.info(f"Wrote output to {output_path}")
