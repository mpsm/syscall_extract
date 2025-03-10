from .model import TypeInfo


def flattened(type_info: TypeInfo):
    """Traverse the type tree, yielding all types."""

    if hasattr(type_info, '__iter__'):
        for item in type_info:
            yield from flattened(item)
        return

    yield type_info
    if type_info.pointer_to:
        yield from flattened(type_info.pointer_to)
    if type_info.array_element:
        yield from flattened(type_info.array_element)
    if type_info.return_type:
        yield from flattened(type_info.return_type)
    if type_info.arguments:
        for arg in type_info.arguments:
            yield from flattened(arg)
    if type_info.struct_fields:
        for field in type_info.struct_fields:
            yield from flattened(field.type_info)
