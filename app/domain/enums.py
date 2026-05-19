from enum import StrEnum


class VectorStatus(StrEnum):
    PENDING = "PENDING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"
