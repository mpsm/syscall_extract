import sys
import os

# Add src directory to path before any local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# fmt: off
from syscall_extract.model import TypeInfo  # noqa: E402
# fmt: on


def test_simple_type_to_argument_name():
    """Test conversion of a simple type to argument name format."""
    # Create a basic int type
    type_info = TypeInfo(name="int")
    assert type_info.to_argument_name("var") == "int var"

    # Create a basic char type
    type_info = TypeInfo(name="char")
    assert type_info.to_argument_name("c") == "char c"


def test_pointer_type_to_argument_name():
    """Test conversion of pointer types to argument name format."""
    # Create a pointer to int
    int_type = TypeInfo(name="int")
    ptr_type = TypeInfo(name="int*", pointer_to=int_type)
    assert ptr_type.to_argument_name("ptr") == "int* ptr"

    # Create a double pointer to char
    char_type = TypeInfo(name="char")
    char_ptr_type = TypeInfo(name="char*", pointer_to=char_type)
    char_ptr_ptr_type = TypeInfo(name="char**", pointer_to=char_ptr_type)
    assert char_ptr_ptr_type.to_argument_name("ptr") == "char** ptr"


def test_array_type_to_argument_name():
    """Test conversion of array types to argument name format."""
    # Create an array of int
    int_type = TypeInfo(name="int")
    array_type = TypeInfo(
        name="int[]",
        is_array=True,
        array_element=int_type
    )
    assert array_type.to_argument_name("arr") == "int arr[]"

    # Create an array of char pointers
    char_type = TypeInfo(name="char")
    char_ptr_type = TypeInfo(name="char*", pointer_to=char_type)
    array_of_ptrs_type = TypeInfo(
        name="char*[]",
        is_array=True,
        array_element=char_ptr_type,
        array_size=2
    )
    assert array_of_ptrs_type.to_argument_name("arr") == "char* arr[2]"


def test_function_pointer_to_argument_name():
    """Test conversion of function pointer types to argument name format."""
    # Create a function pointer returning void and taking an int
    void_type = TypeInfo(name="void")
    int_type = TypeInfo(name="int")
    func_ptr_type = TypeInfo(
        name="void (*)(int)",
        is_function=True,
        return_type=void_type,
        arguments=[int_type]
    )
    assert func_ptr_type.to_argument_name("callback") == "void (*callback)(int)"

    # Create a more complex function pointer
    char_type = TypeInfo(name="char")
    char_ptr_type = TypeInfo(name="char*", pointer_to=char_type)
    complex_func_type = TypeInfo(
        name="int (*)(char*, int)",
        is_function=True,
        return_type=int_type,
        arguments=[char_ptr_type, int_type]
    )
    assert complex_func_type.to_argument_name("parser") == "int (*parser)(char*, int)"
