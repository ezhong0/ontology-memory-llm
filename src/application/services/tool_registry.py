"""Auto-generate LLM tool definitions from domain ports.

Vision Alignment:
- Declarative (not hardcoded)
- Derives from source of truth (port interface)
- Type-safe (uses Python type hints)
- Self-documenting (uses docstrings)
"""

import inspect
from dataclasses import dataclass
from typing import Any, get_args, get_origin

from src.domain.ports.domain_database_port import DomainDatabasePort


@dataclass(frozen=True)
class ToolDefinition:
    """LLM tool definition in Claude format."""

    name: str
    description: str
    input_schema: dict[str, Any]


class ToolRegistry:
    """Generate tool definitions from port methods.

    Philosophy: Tools are not hardcoded. They emerge from the domain model.

    When DomainDatabasePort changes, tools automatically update.
    This is declarative programming: describe the interface, derive the tools.
    """

    def __init__(self, domain_db_port_class: type[DomainDatabasePort]):
        """Initialize with port interface class.

        Args:
            domain_db_port_class: The DomainDatabasePort class (not instance)
        """
        self.port_class = domain_db_port_class

    def generate_tools(self) -> list[ToolDefinition]:
        """Generate tool definitions from all port methods.

        Uses:
        - Method name → tool name
        - Docstring → tool description
        - Type hints → input schema

        Returns:
            List of tool definitions ready for LLM
        """
        tools: list[ToolDefinition] = []

        # Get all abstract methods from the port interface
        for method_name in dir(self.port_class):
            # Skip private methods and built-in methods
            if method_name.startswith("_"):
                continue

            method = getattr(self.port_class, method_name)

            # Only process callable methods
            if not callable(method):
                continue

            # Extract method signature
            try:
                sig = inspect.signature(method)
            except (ValueError, TypeError):
                # Skip methods without inspectable signatures
                continue

            # Build input schema from type hints
            properties: dict[str, Any] = {}
            required: list[str] = []

            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue

                # Extract type annotation
                param_type = param.annotation
                if param_type == inspect.Parameter.empty:
                    # No type hint, default to string
                    param_type = str

                json_type = self._python_type_to_json_type(param_type)

                properties[param_name] = {"type": json_type}

                # Add description from docstring if available
                if method.__doc__:
                    param_desc = self._extract_param_description(
                        method.__doc__, param_name
                    )
                    if param_desc:
                        properties[param_name]["description"] = param_desc

                # Required if no default value
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            # Extract description from docstring (first line)
            description = (
                method.__doc__.strip().split("\n")[0].strip()
                if method.__doc__
                else f"Execute {method_name}"
            )

            tools.append(
                ToolDefinition(
                    name=method_name,
                    description=description,
                    input_schema={
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                )
            )

        return tools

    def _python_type_to_json_type(self, python_type: Any) -> str:
        """Map Python type hints to JSON schema types.

        Args:
            python_type: Python type annotation

        Returns:
            JSON schema type string
        """
        # Handle Optional[X] (which is Union[X, None])
        origin = get_origin(python_type)
        if origin is type(None) or python_type is type(None):
            return "string"  # Default for None

        # Handle Union types (e.g., str | None)
        if origin is not None:
            # Get the args of the union
            args = get_args(python_type)
            if args:
                # Take the first non-None type
                for arg in args:
                    if arg is not type(None):
                        python_type = arg
                        break

        # Map basic types
        if python_type == str or python_type == "str":
            return "string"
        elif python_type == int or python_type == "int":
            return "integer"
        elif python_type == bool or python_type == "bool":
            return "boolean"
        elif python_type == float or python_type == "float":
            return "number"
        elif python_type == dict or python_type == "dict":
            return "object"
        elif python_type == list or python_type == "list":
            return "array"
        else:
            # Default fallback
            return "string"

    def _extract_param_description(self, docstring: str, param_name: str) -> str | None:
        """Extract parameter description from docstring Args section.

        Args:
            docstring: Method docstring
            param_name: Parameter name to find

        Returns:
            Description string or None if not found
        """
        lines = docstring.split("\n")
        in_args = False

        for line in lines:
            stripped = line.strip()

            if "Args:" in stripped:
                in_args = True
                continue

            if in_args:
                # Check if we've left the Args section
                if stripped.startswith("Returns:") or stripped.startswith("Raises:"):
                    break

                # Check if this line contains the parameter
                if stripped.startswith(f"{param_name}:"):
                    # Extract description after colon
                    desc = stripped.split(":", 1)[1].strip()
                    return desc

        return None
