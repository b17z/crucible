"""Result types for errors as values."""

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Ok(Generic[T]):
    """Success result containing a value."""

    value: T

    @property
    def is_ok(self) -> bool:
        return True

    @property
    def is_err(self) -> bool:
        return False


@dataclass(frozen=True)
class Err(Generic[E]):
    """Error result containing an error."""

    error: E

    @property
    def is_ok(self) -> bool:
        return False

    @property
    def is_err(self) -> bool:
        return True


Result = Ok[T] | Err[E]


def ok(value: T) -> Ok[T]:
    """Create a success result."""
    return Ok(value)


def err(error: E) -> Err[E]:
    """Create an error result."""
    return Err(error)
