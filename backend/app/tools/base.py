from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, Type, TypeVar

from pydantic import BaseModel


InputSchemaT = TypeVar("InputSchemaT", bound=BaseModel)
OutputSchemaT = TypeVar("OutputSchemaT", bound=BaseModel)


class BaseTool(ABC, Generic[InputSchemaT, OutputSchemaT]):
    """Common contract for every application tool.

    A tool exposes metadata and schemas to the agent/LLM, while the
    application remains responsible for executing the actual operation.

    This class intentionally has no knowledge of:
    - PostgreSQL
    - RAG
    - Gemini
    - web APIs
    - LangGraph

    Concrete tools should implement only their own application capability.
    """

    name: str
    description: str
    input_schema: Type[InputSchemaT]
    output_schema: Type[OutputSchemaT]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Validate the required tool metadata at class-definition time."""
        super().__init_subclass__(**kwargs)

        required_attributes = (
            "name",
            "description",
            "input_schema",
            "output_schema",
        )

        missing = [
            attribute
            for attribute in required_attributes
            if not getattr(cls, attribute, None)
        ]

        if missing:
            raise TypeError(
                f"{cls.__name__} must define: {', '.join(missing)}"
            )

    def validate_input(self, arguments: InputSchemaT | dict[str, Any]) -> InputSchemaT:
        """Validate raw tool arguments using the declared Pydantic schema."""
        if isinstance(arguments, self.input_schema):
            return arguments

        return self.input_schema.model_validate(arguments)

    def validate_output(self, result: OutputSchemaT | dict[str, Any]) -> OutputSchemaT:
        """Validate and normalize the structured result returned by a tool."""
        if isinstance(result, self.output_schema):
            return result

        return self.output_schema.model_validate(result)

    def get_definition(self) -> dict[str, Any]:
        """Return the framework-neutral tool definition.

        Later, the LLM integration layer can transform this definition into
        the exact function/tool schema required by the selected model SDK.
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema.model_json_schema(),
            "output_schema": self.output_schema.model_json_schema(),
        }

    @abstractmethod
    def execute(self, arguments: InputSchemaT) -> OutputSchemaT:
        """Execute the tool using already-validated arguments."""
        raise NotImplementedError
