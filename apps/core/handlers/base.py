"""
Base handler classes for CAD processing pipelines.

Provides BaseCADHandler, CADHandlerResult, CADHandlerError,
and CADHandlerPipeline — shared across all handler apps.

Source: bfagent/apps/cad_hub/handlers/base.py
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


class CADFormat(Enum):
    """Unterstützte CAD-Formate."""

    IFC = "ifc"
    DXF = "dxf"
    DWG = "dwg"
    UNKNOWN = "unknown"

    @classmethod
    def from_extension(
        cls, filepath: Union[str, Path]
    ) -> "CADFormat":
        ext = Path(filepath).suffix.lower()
        mapping = {
            ".ifc": cls.IFC,
            ".dxf": cls.DXF,
            ".dwg": cls.DWG,
        }
        return mapping.get(ext, cls.UNKNOWN)


class HandlerStatus(Enum):
    """Handler-Ausführungsstatus."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class CADHandlerResult:
    """Ergebnis eines Handler-Aufrufs."""

    success: bool
    handler_name: str
    status: HandlerStatus = HandlerStatus.SUCCESS
    data: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    execution_time_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    def to_dict(self) -> dict:
        serializable_data = {
            k: v
            for k, v in self.data.items()
            if not k.startswith("_")
        }
        return {
            "success": self.success,
            "handler": self.handler_name,
            "status": self.status.value,
            "data": serializable_data,
            "errors": self.errors,
            "warnings": self.warnings,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp,
        }

    def add_error(self, message: str):
        self.errors.append(message)
        self.success = False
        self.status = HandlerStatus.ERROR

    def add_warning(self, message: str):
        self.warnings.append(message)


class CADHandlerError(Exception):
    """Exception für Handler-Fehler."""

    def __init__(
        self,
        message: str,
        handler_name: str = "",
        details: dict = None,
    ):
        self.message = message
        self.handler_name = handler_name
        self.details = details or {}
        super().__init__(message)


class BaseCADHandler(ABC):
    """
    Basisklasse für alle CAD Handler.

    Handler verarbeiten CAD-Daten in einer Pipeline:
    INPUT -> PROCESSING -> OUTPUT
    """

    name: str = "BaseHandler"
    description: str = "Basisklasse für CAD Handler"
    required_inputs: list = []
    optional_inputs: list = []

    def __init__(self, context: dict = None):
        self.context = context or {}
        self._start_time: Optional[datetime] = None
        self._result: Optional[CADHandlerResult] = None

    @abstractmethod
    def execute(
        self, input_data: dict
    ) -> CADHandlerResult:
        pass

    def validate_input(
        self, input_data: dict
    ) -> tuple[bool, list[str]]:
        errors = []
        for required in self.required_inputs:
            if (
                required not in input_data
                and required not in self.context
            ):
                errors.append(
                    f"Pflichtfeld fehlt: {required}"
                )
        return len(errors) == 0, errors

    def run(self, input_data: dict) -> CADHandlerResult:
        self._start_time = datetime.now()
        merged_input = {**self.context, **input_data}

        valid, errors = self.validate_input(merged_input)
        if not valid:
            return CADHandlerResult(
                success=False,
                handler_name=self.name,
                status=HandlerStatus.ERROR,
                errors=errors,
            )

        try:
            logger.info(
                "[%s] Starting execution...", self.name
            )
            result = self.execute(merged_input)
            elapsed = (
                datetime.now() - self._start_time
            ).total_seconds() * 1000
            result.execution_time_ms = elapsed
            logger.info(
                "[%s] Completed in %.1fms",
                self.name,
                elapsed,
            )
            return result
        except CADHandlerError as e:
            logger.error(
                "[%s] Handler error: %s",
                self.name,
                e.message,
            )
            return CADHandlerResult(
                success=False,
                handler_name=self.name,
                status=HandlerStatus.ERROR,
                errors=[e.message],
            )
        except Exception as e:
            logger.exception(
                "[%s] Unexpected error: %s",
                self.name,
                e,
            )
            return CADHandlerResult(
                success=False,
                handler_name=self.name,
                status=HandlerStatus.ERROR,
                errors=[f"Unerwarteter Fehler: {e!s}"],
            )

    def update_context(self, key: str, value: Any):
        self.context[key] = value

    def get_from_context(
        self, key: str, default: Any = None
    ) -> Any:
        return self.context.get(key, default)

    def __repr__(self):
        cls = self.__class__.__name__
        return f"<{cls}(name={self.name})>"


class CADHandlerPipeline:
    """Pipeline für sequentielle Handler-Ausführung."""

    def __init__(self, context: dict = None):
        self.handlers: list[BaseCADHandler] = []
        self.context = context or {}
        self.results: list[CADHandlerResult] = []

    def add(
        self, handler: BaseCADHandler
    ) -> "CADHandlerPipeline":
        handler.context = self.context
        self.handlers.append(handler)
        return self

    def run(
        self, input_data: dict
    ) -> list[CADHandlerResult]:
        self.results = []
        current_data = {**self.context, **input_data}

        for handler in self.handlers:
            handler.context = current_data
            result = handler.run(current_data)
            self.results.append(result)

            if not result.success:
                logger.warning(
                    "Pipeline stopped at %s: %s",
                    handler.name,
                    result.errors,
                )
                break

            current_data.update(result.data)

        return self.results

    def get_final_result(self) -> dict:
        combined = {
            "success": all(
                r.success for r in self.results
            ),
            "handlers": [
                r.to_dict() for r in self.results
            ],
            "data": {},
            "errors": [],
            "warnings": [],
        }

        for result in self.results:
            serializable_data = {
                k: v
                for k, v in result.data.items()
                if not k.startswith("_")
            }
            combined["data"].update(serializable_data)
            combined["errors"].extend(result.errors)
            combined["warnings"].extend(result.warnings)

        return combined
