import logging
import os
import tempfile
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Tuple, Optional

from clang.cindex import Index, CursorKind, TranslationUnit, TypeKind


class TypeQualifier(Enum):
    CONST = auto()
    VOLATILE = auto()
    RESTRICT = auto()


class StorageClass(Enum):
    AUTO = auto()
    REGISTER = auto()
    STATIC = auto()
    EXTERN = auto()
    TYPEDEF = auto()


class StructType(Enum):
    STRUCT = auto()
    UNION = auto()
    ENUM = auto()


@dataclass
class TypeInfo:
    name: str
    base_type: Optional[str] = None
    qualifiers: List[TypeQualifier] = None
    storage_class: Optional[StorageClass] = None

    pointer_to: Optional["TypeInfo"] = None

    is_array: bool = False
    array_size: Optional[int] = None
    array_element: Optional["TypeInfo"] = None

    is_function: bool = False
    return_type: Optional["TypeInfo"] = None
    arguments: Optional[List["TypeInfo"]] = None

    is_structural: bool = False
    struct_type: Optional[StructType] = None
    struct_fields: Optional[List["TypeInfo"]] = None

    def is_primitive(self) -> bool:
        return (
            self.base_type == self.name
            and not self.is_structural
            and not self.is_array
            and not self.is_function
            and self.qualifiers is None
            and self.storage_class is None
        )


@dataclass
class Typedef:
    name: str
    underlying_type: str


@dataclass
class FunctionArg:
    name: str
    type: str


@dataclass
class Function:
    name: str
    return_type: str
    arguments: List[FunctionArg]


def extract_type_info(clang_type) -> TypeInfo:
    """Extract detailed type information from a clang type."""

    logging.debug(f"Extracting type info for {clang_type.spelling}")

    # Extract qualifiers
    qualifiers = []
    coc = ""
    if clang_type.is_const_qualified():
        qualifiers.append(TypeQualifier.CONST)
        coc += "const "
    if clang_type.is_volatile_qualified():
        qualifiers.append(TypeQualifier.VOLATILE)
        coc += "volatile "
    if clang_type.is_restrict_qualified():
        qualifiers.append(TypeQualifier.RESTRICT)
        coc += "restrict"

    coc = coc.strip()
    base_name = clang_type.get_canonical().spelling
    if clang_type.kind == TypeKind.POINTER:
        base_name = base_name.removesuffix(coc).strip()
    else:
        base_name = base_name.removeprefix(coc).strip()

    # Pointer handling
    if clang_type.kind == TypeKind.POINTER:
        pointee = clang_type.get_pointee()
        pointee_info = extract_type_info(pointee)

        return TypeInfo(
            name=clang_type.spelling,
            base_type=base_name,
            qualifiers=qualifiers,
            pointer_to=pointee_info,
        )

    # Array handling - now handles both CONSTANTARRAY and INCOMPLETEARRAY
    elif clang_type.kind in (TypeKind.CONSTANTARRAY, TypeKind.INCOMPLETEARRAY):
        element_type = clang_type.get_array_element_type()
        element_info = extract_type_info(element_type)

        # For constant arrays, get the size, for incomplete arrays it's None
        array_size = None
        if clang_type.kind == TypeKind.CONSTANTARRAY:
            array_size = clang_type.get_array_size()

        # Create a more descriptive base_type that includes the brackets notation
        formatted_base_type = f"{element_info.name}[]"

        return TypeInfo(
            name=clang_type.spelling,
            base_type=formatted_base_type,
            qualifiers=qualifiers,
            is_array=True,
            array_size=array_size,
            array_element=element_info,
        )

    # Function pointer handling
    elif clang_type.kind == TypeKind.FUNCTIONPROTO:
        return_type_info = extract_type_info(clang_type.get_result())
        arg_types = []

        for i in range(clang_type.get_num_arg_types()):
            arg_type = clang_type.get_arg_type(i)
            arg_types.append(extract_type_info(arg_type))

        return TypeInfo(
            name=clang_type.spelling,
            base_type=base_name,
            qualifiers=qualifiers,
            is_function=True,
            return_type=return_type_info,
            arguments=arg_types,
        )

    # Struct, union, enum handling
    elif clang_type.kind == TypeKind.RECORD:
        decl = clang_type.get_declaration()
        struct_type = None

        if decl.kind == CursorKind.STRUCT_DECL:
            struct_type = StructType.STRUCT
        elif decl.kind == CursorKind.UNION_DECL:
            struct_type = StructType.UNION

        # We could extract fields here but it would require additional traversal
        return TypeInfo(
            name=clang_type.spelling,
            base_type=base_name,
            qualifiers=qualifiers,
            is_structural=True,
            struct_type=struct_type,
        )

    # Enum handling
    elif clang_type.kind == TypeKind.ENUM:
        return TypeInfo(
            name=clang_type.spelling,
            base_type=base_name,
            qualifiers=qualifiers,
            is_structural=True,
            struct_type=StructType.ENUM,
        )

    # Typedef handling
    elif clang_type.kind == TypeKind.TYPEDEF:
        storage_class = StorageClass.TYPEDEF
        underlying = clang_type.get_canonical()

        return TypeInfo(
            name=clang_type.spelling,
            base_type=underlying.spelling,
            qualifiers=qualifiers,
            storage_class=storage_class,
        )

    # Basic types
    else:
        return TypeInfo(
            name=clang_type.spelling,
            base_type=base_name,
            qualifiers=qualifiers,
        )


def extract_extern_functions(
    header_content: str, header_name: str
) -> Tuple[List[Function], List[Typedef], Dict[str, TypeInfo]]:
    """Extract extern function information from header content using libclang."""
    logging.debug(f"Extracting extern functions from {header_name}")

    # Create a temporary file with header content
    with tempfile.NamedTemporaryFile(suffix=".h", mode="w", delete=False) as temp:
        temp.write(header_content)
        temp_filename = temp.name

    try:
        # Parse the file with libclang
        index = Index.create()
        tu = index.parse(
            temp_filename, options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
        )

        extern_functions = []
        typedefs = []
        type_store = {}

        # Find all function declarations with external linkage
        for cursor in tu.cursor.walk_preorder():
            if cursor.kind == CursorKind.FUNCTION_DECL:
                # Check if it's an extern function
                try:
                    if cursor.linkage.value != 0:  # Non-zero linkage means external
                        function_name = cursor.spelling
                        # Extract detailed return type info
                        return_type = cursor.result_type.spelling
                        type_store[return_type] = extract_type_info(cursor.result_type)

                        # Get arguments with detailed type info
                        args = []
                        for arg in cursor.get_arguments():
                            arg_name = arg.spelling or ""  # Use empty string if no name
                            arg_type = arg.type.spelling
                            type_store[arg_type] = extract_type_info(arg.type)
                            args.append(FunctionArg(name=arg_name, type=arg_type))

                        # Create Function object
                        func = Function(
                            name=function_name,
                            return_type=return_type,
                            arguments=args,
                        )

                        extern_functions.append(func)
                        logging.debug(f"Found extern function: {function_name}")
                except Exception as e:
                    # Some cursors might not have linkage information
                    logging.debug(f"Error processing function: {e}")
                    pass
            elif cursor.kind == CursorKind.TYPEDEF_DECL:
                try:
                    typedef_name = cursor.spelling

                    # Extract detailed type information
                    underlying_type = cursor.underlying_typedef_type.spelling
                    underlying_type_info = extract_type_info(
                        cursor.underlying_typedef_type
                    )
                    type_store[underlying_type] = underlying_type_info

                    typedefs.append(
                        Typedef(
                            name=typedef_name,
                            underlying_type=underlying_type,
                        )
                    )
                    logging.debug(
                        f"Found typedef: {typedef_name} -> {underlying_type_info.name}"
                    )
                except Exception as e:
                    logging.debug(f"Error processing typedef: {e}")
                    pass

        logging.info(
            f"Found {len(extern_functions)} extern functions and {len(typedefs)} typedefs in {header_name}"
        )
        logging.info(f"Extracted {len(type_store)} unique type definitions")
        return extern_functions, typedefs, type_store

    except Exception as e:
        logging.error(f"Error processing {header_name} with libclang: {e}")
        return [], [], []

    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_filename)
        except:
            pass


def process_expanded_headers(
    expanded_headers: Dict[str, str],
) -> Dict[str, Tuple[List[Function], List[Typedef]]]:
    """Process expanded headers to extract extern function and typedef information."""
    header_elements = {}

    for header, content in expanded_headers.items():
        if content:
            header_elements[header] = extract_extern_functions(content, header)

    return header_elements
