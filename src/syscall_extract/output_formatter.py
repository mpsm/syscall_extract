import json
import logging
import os
from collections import defaultdict, OrderedDict

from .dataclass_serialization import DataclassJSONEncoder, dataclass_to_dict
from .model import SyscallsContext, StorageClass, StructType, TypeInfo
from .type_utils import flattened, get_unqualified_type_name


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


def get_types_to_add(syscalls_ctx: SyscallsContext) -> list:
    types_to_add = OrderedDict()
    types_added = set()

    def check_and_add(flat_type, types_to_add, types_added):
        flat_type_name = get_unqualified_type_name(flat_type)
        logging.debug(f"Checking type {flat_type_name}")
        if (flat_type.is_elaborated or flat_type.storage_class == StorageClass.TYPEDEF):
            if flat_type_name in types_added:
                logging.debug(f"Type {flat_type_name} already added")
                type_added = types_to_add[flat_type_name]
                if not type_added.is_structural:
                    return

                if type_added.struct_anonymous:
                    return

                if type_added.struct_type == StructType.ENUM and \
                        type_added.enum_constants is not None and len(type_added.enum_constants) > 0:
                    return

                if type_added.struct_fields is not None and len(type_added.struct_fields) > 0:
                    return

            logging.debug(f"Adding type {flat_type_name}")
            types_to_add[flat_type_name] = flat_type
            types_added.add(flat_type_name)
            logging.debug(
                f"Adding type {flat_type_name} to the output list. Root type: {flat_type_name}")

    for _, syscall in sorted(syscalls_ctx.syscalls.items()):
        if syscall.function:
            return_type_info = syscalls_ctx.type_store[syscall.function.return_type]
            for flat_type in reversed(list(flattened(return_type_info))):
                check_and_add(flat_type, types_to_add, types_added)
            for arg in syscall.function.arguments:
                arg_type_info = syscalls_ctx.type_store[arg.type]
                for flat_type in reversed(list(flattened(arg_type_info))):
                    check_and_add(flat_type, types_to_add, types_added)

    return types_to_add.values()


C_INDENT = 4*" "


def output_c_struct(struct_info: TypeInfo, indent=None, no_indent=None) -> list:
    lines = []
    if indent is None:
        indent = C_INDENT
    if no_indent is None:
        no_indent = ""

    struct_name = struct_info.base_type

    if struct_info.struct_anonymous:
        lines.append(f"{no_indent}{struct_info.struct_type.name.lower()} {{")
    else:
        lines.append(f"{no_indent}{struct_name} {{")

    for field in struct_info.struct_fields:
        if field.type_info.is_array:
            lines.append(
                f"{indent}{get_unqualified_type_name(field.type_info.array_element)} "
                f"{field.name}[{field.type_info.array_size}];"
            )
        elif field.type_info.is_structural and (not field.type_info.is_elaborated
                                                or field.type_info.struct_anonymous):
            new_lines = output_c_struct(field.type_info, indent + C_INDENT, no_indent + C_INDENT)
            if field.type_info.struct_anonymous:
                new_lines[-1] = f"{no_indent+C_INDENT}}} {field.name};"
            lines.extend(new_lines)
        elif field.type_info.is_pointer() and field.type_info.pointer_to.is_function:
            function = field.type_info.pointer_to
            field_line = f"{function.return_type.name} (*{field.name})("
            field_line += ", ".join(arg.name for arg in function.arguments)
            field_line += ");"
            lines.append(f"{indent}{field_line}")
        else:
            lines.append(f"{indent}{get_unqualified_type_name(field.type_info)} {field.name};")
    lines.append(f"{no_indent}}};")

    return lines


def output_c_enum(enum_info: TypeInfo) -> list:
    lines = []

    lines.append(f"enum {enum_info.base_type} {{")
    for constant in enum_info.enum_constants:
        if constant.value is None:
            lines.append(f"{C_INDENT}{constant.name},")
        else:
            lines.append(f"{C_INDENT}{constant.name} = {constant.value},")

    lines.append("};")

    return lines


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
        "",
        "#ifndef restrict",
        "#define restrict __restrict",
        "#endif",
        "",
    ]

    lines.append("/* Type definitions */")
    types_to_add = get_types_to_add(syscalls_ctx)
    types_added = set()
    struct_lines = []
    for type_info in types_to_add:
        unqualified_name = get_unqualified_type_name(type_info)
        if unqualified_name in types_added:
            continue

        logging.debug(f"Adding type {unqualified_name} to the output list")

        if type_info.is_basic_type() or type_info.is_pointer() or (type_info.is_typedef
                                                                   and (type_info.underlying_type.is_basic_type() or
                                                                        type_info.underlying_type.is_pointer())):
            lines.append(f"typedef {type_info.base_type} {unqualified_name};")
            types_added.add(unqualified_name)
        elif type_info.is_elaborated and type_info.is_structural:
            struct_kind = type_info.struct_type.name.lower()

            if type_info.struct_anonymous:
                continue
            elif not unqualified_name.startswith(struct_kind):
                if type_info.struct_type == StructType.ENUM:
                    new_struct_lines = output_c_enum(type_info)
                else:
                    new_struct_lines = output_c_struct(type_info)
                if not new_struct_lines[0].startswith(struct_kind):
                    new_struct_lines[0] = f"{struct_kind} " + new_struct_lines[0]

                new_struct_lines[0] = f"typedef {new_struct_lines[0]}"
                new_struct_lines[-1] = new_struct_lines[-1].strip(';')
                new_struct_lines[-1] = f"{new_struct_lines[-1]} {unqualified_name};"
                struct_lines.extend(new_struct_lines)
            else:
                struct_lines.extend(output_c_struct(type_info))
            types_added.add(unqualified_name)
            struct_lines.append("")

    lines.append("")
    lines.extend(struct_lines)
    lines.append("")

    lines.extend(
        [
            "/* Syscall function prototypes */",
        ]
    )

    for _, syscall in sorted(syscalls_ctx.syscalls.items()):
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
