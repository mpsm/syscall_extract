from syscall_extract.model import TypeInfo, TypeQualifier
import sys
import os
import unittest

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))


class TestTypeInfo(unittest.TestCase):
    def test_simple_type_to_argument_name(self):
        """Test conversion of a simple type to argument name format."""
        # Create a basic int type
        type_info = TypeInfo(name="int")
        self.assertEqual(type_info.to_argument_name("var"), "int var")

        # Create a basic char type
        type_info = TypeInfo(name="char")
        self.assertEqual(type_info.to_argument_name("c"), "char c")

    def test_pointer_type_to_argument_name(self):
        """Test conversion of pointer types to argument name format."""
        # Create a pointer to int
        int_type = TypeInfo(name="int")
        ptr_type = TypeInfo(name="int*", pointer_to=int_type)
        self.assertEqual(ptr_type.to_argument_name("ptr"), "int* ptr")

        # Create a double pointer to char
        char_type = TypeInfo(name="char")
        char_ptr_type = TypeInfo(name="char*", pointer_to=char_type)
        char_ptr_ptr_type = TypeInfo(name="char**", pointer_to=char_ptr_type)
        self.assertEqual(char_ptr_ptr_type.to_argument_name("ptr"), "char** ptr")

    def test_array_type_to_argument_name(self):
        """Test conversion of array types to argument name format."""
        # Create an array of int
        int_type = TypeInfo(name="int")
        array_type = TypeInfo(
            name="int[]",
            is_array=True,
            array_element=int_type
        )
        self.assertEqual(array_type.to_argument_name("arr"), "int[] arr")

        # Create an array of char pointers
        char_type = TypeInfo(name="char")
        char_ptr_type = TypeInfo(name="char*", pointer_to=char_type)
        array_of_ptrs_type = TypeInfo(
            name="char*[]",
            is_array=True,
            array_element=char_ptr_type
        )
        self.assertEqual(array_of_ptrs_type.to_argument_name("arr"), "char*[] arr")

    def test_function_pointer_to_argument_name(self):
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
        self.assertEqual(
            func_ptr_type.to_argument_name("callback"),
            "void (*callback)(int)"
        )

        # Create a more complex function pointer
        char_type = TypeInfo(name="char")
        char_ptr_type = TypeInfo(name="char*", pointer_to=char_type)
        complex_func_type = TypeInfo(
            name="int (*)(char*, int)",
            is_function=True,
            return_type=int_type,
            arguments=[char_ptr_type, int_type]
        )
        self.assertEqual(
            complex_func_type.to_argument_name("parser"),
            "int (*parser)(char*, int)"
        )

    def test_complex_nested_types_to_argument_name(self):
        """Test conversion of complex nested types to argument name format."""
        # Create a pointer to an array of ints
        int_type = TypeInfo(name="int")
        int_array_type = TypeInfo(
            name="int[]",
            is_array=True,
            array_element=int_type
        )
        ptr_to_array_type = TypeInfo(
            name="int (*)[10]",
            pointer_to=int_array_type
        )
        self.assertEqual(ptr_to_array_type.to_argument_name("matrix"), "int (*)[] matrix")

        # Create an array of function pointers
        void_type = TypeInfo(name="void")
        func_ptr_type = TypeInfo(
            name="void (*)()",
            is_function=True,
            return_type=void_type,
            arguments=[]
        )
        array_of_func_ptrs = TypeInfo(
            name="void (*[])()",
            is_array=True,
            array_element=func_ptr_type
        )
        self.assertEqual(
            array_of_func_ptrs.to_argument_name("callbacks"),
            "void (*)()[] callbacks"
        )


if __name__ == '__main__':
    unittest.main()
