from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, computed_field


class IssueCategory(StrEnum):
    EXCLUDED = "excluded"
    DUPLICATE = "duplicate"
    MISSING_OR_STATUS = "missing"
    MISMATCH = "mismatch"

class IssueCode(StrEnum):
    BAD_COLUMN_COUNT = "BAD_COLUMN_COUNT"
    PARENT_REJECTED = "PARENT_REJECTED"
    NAME_CONFLICT = "NAME_CONFLICT"
    INVENTORY_CONFLICT = "INVENTORY_CONFLICT"
    NO_PARENT = "NO_PARENT"
    DUP_IN_SOURCE = "DUP_IN_SOURCE"
    DUP_CROSS_SOURCE = "DUP_CROSS_SOURCE"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_STATUS = "INVALID_STATUS"
    BAD_FORMAT = "BAD_FORMAT"
    INVALID_ASSET_TYPE = "INVALID_ASSET_TYPE"
    FIELD_MISMATCH = "FIELD_MISMATCH"
    MISSING_IN_SOURCE = "MISSING_IN_SOURCE"

CODE_CATEGORY: dict[IssueCode, IssueCategory] = {
    IssueCode.BAD_COLUMN_COUNT: IssueCategory.EXCLUDED,
    IssueCode.PARENT_REJECTED: IssueCategory.EXCLUDED,
    IssueCode.NAME_CONFLICT: IssueCategory.EXCLUDED,
    IssueCode.INVENTORY_CONFLICT: IssueCategory.EXCLUDED,
    IssueCode.NO_PARENT: IssueCategory.EXCLUDED,
    IssueCode.DUP_IN_SOURCE: IssueCategory.DUPLICATE,
    IssueCode.DUP_CROSS_SOURCE: IssueCategory.DUPLICATE,
    IssueCode.MISSING_FIELD: IssueCategory.MISSING_OR_STATUS,
    IssueCode.INVALID_STATUS: IssueCategory.MISSING_OR_STATUS,
    IssueCode.BAD_FORMAT: IssueCategory.MISSING_OR_STATUS,
    IssueCode.INVALID_ASSET_TYPE: IssueCategory.MISSING_OR_STATUS,
    IssueCode.FIELD_MISMATCH: IssueCategory.MISMATCH,
    IssueCode.MISSING_IN_SOURCE: IssueCategory.MISMATCH
}

class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class AssetCategory(StrEnum):
    ENDPOINT = "endpoint"
    NETWORK = "network"
    PERIPHERAL = "peripheral"
    ADAPTER = "adapter"


class MatchStatus(StrEnum):
    MATCHED = "matched"
    ONLY_IN_SOURCE = "only_in_source"
    AMBIGUOUS = "ambiguous"


class MatchMethod(StrEnum):
    INVENTORY_NUMBER = "inventory_number"
    SERIAL_NUMBER = "serial_number"
    NAME = "name"
    FUZZY = "fuzzy"

class RowRef(BaseModel):
    source_id: int
    batch_id: int
    row_number: int

class NormalizedRecord(BaseModel):
    ref: RowRef

    inventory_number: str | None = None
    serial_number: str | None = None

    name: str | None = None
    asset_type: str | None = None
    category: AssetCategory | None = None
    manufacturer: str | None = None
    model: str | None = None
    specs: str | None = None

    status: str | None = None
    status_raw: str | None = None
    responsible_person: str | None = None
    location: str | None = None
    commissioning_date: date | None = None

    raw: dict[str, str] = Field(default_factory=dict)

class ParseResult(BaseModel):
    records: list[NormalizedRecord]
    issues: list[Issue]

class AssetGroup(BaseModel):
    asset_key: str
    records: list[NormalizedRecord]
    match_status: MatchStatus
    match_method: MatchMethod | None = None
    match_score: float | None = None


class FieldValue(BaseModel):
    ref: RowRef
    value: str | None = None


class Issue(BaseModel):
    code: IssueCode
    severity: Severity
    message: str

    refs: list[RowRef] = Field(default_factory=list)
    asset_key: str | None = None
    field: str | None = None

    values: list[FieldValue] = Field(default_factory=list)
    suggestion: str | None = None

    @computed_field
    @property
    def category(self) -> IssueCategory:
        return CODE_CATEGORY[self.code]

