import json
import dataclasses
import enum
from typing import Any, Dict


class DataclassJSONEncoder(json.JSONEncoder):
    """JSON encoder for dataclasses."""

    def default(self, obj: Any) -> Any:
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        # Handle enum types
        if isinstance(obj, enum.Enum):
            return obj.name  # Use enum name for cleaner output
        return super().default(obj)


def dataclass_to_dict(obj: Any) -> Dict:
    """Convert a dataclass instance to a dictionary."""
    if dataclasses.is_dataclass(obj):
        result = {}
        for field in dataclasses.fields(obj):
            value = getattr(obj, field.name)
            if value is not None:
                result[field.name] = dataclass_to_dict(value)
        return result
    elif isinstance(obj, enum.Enum):
        # Handle Enum values
        return obj.name  # Or use obj.value if you prefer the numerical value
    elif isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: dataclass_to_dict(value) for key, value in obj.items()}
    else:
        return obj
