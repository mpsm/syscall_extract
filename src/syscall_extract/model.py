from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, ForwardRef


TypeInfo = ForwardRef('TypeInfo')


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
class EnumConstant:
    """Represents a constant in an enum"""
    name: str
    value: Optional[int] = None


@dataclass
class StructField:
    """Represents a field in a struct or union"""
    name: str
    type_info: TypeInfo


@dataclass
class TypeInfo:
    name: str
    base_type: Optional[str] = None
    qualifiers: List[TypeQualifier] = None
    storage_class: Optional[StorageClass] = None

    is_typedef: bool = False
    underlying_type: Optional[TypeInfo] = None

    pointer_to: Optional["TypeInfo"] = None

    is_array: bool = False
    array_size: Optional[int] = None
    array_element: Optional[TypeInfo] = None

    is_function: bool = False
    return_type: Optional[TypeInfo] = None
    arguments: Optional[List[TypeInfo]] = None

    is_structural: bool = False
    struct_type: Optional[StructType] = None
    struct_fields: Optional[List[StructField]] = None
    struct_anonymous: bool = False

    enum_constants: Optional[List[EnumConstant]] = None

    is_elaborated: bool = False

    def is_basic_type(self) -> bool:
        return not self.is_array and not self.is_function and not self.is_structural and not self.is_pointer() \
            and not self.is_typedef

    def is_primitive(self) -> bool:
        return (
            self.base_type == self.name
            and not self.is_structural
            and not self.is_array
            and not self.is_function
            and self.qualifiers is None
            and self.storage_class is None
        )

    def is_pointer(self) -> bool:
        return self.pointer_to is not None

    def to_argument_name(self, argument_name: str) -> str:
        if self.is_pointer():
            return f"{self.name} {argument_name}"
        elif self.is_array:
            arg_name = f"{self.array_element.name} {argument_name}"
            if self.array_size is not None:
                arg_name += f"[{self.array_size}]"
            else:
                arg_name += "[]"
            return arg_name
        elif self.is_function:
            arg_name = f"{self.return_type.name} (*{argument_name})("
            arg_name += ", ".join(arg.name for arg in self.arguments)
            arg_name += ")"
            return arg_name
        else:
            return self.name + " " + argument_name


@dataclass
class Typedef:
    name: str
    underlying_type: str

    def __hash__(self):
        return hash(self.name)


@dataclass
class FunctionArg:
    name: str
    type: str


@dataclass
class Function:
    name: str
    return_type: str
    arguments: List[FunctionArg]


@dataclass
class Syscall:
    name: str
    number: int
    header_name: str
    function: Optional[Function] = None


@dataclass
class SyscallsContext:
    syscalls: Dict[int, Syscall]
    typedefs: List[Typedef]
    type_store: Dict[str, TypeInfo]
