from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class SourceInputSchema(BaseModel):
    name: str = Field(min_length=4, max_length=100)
    description: str | None = Field(default=None, min_length=4, max_length=500)

    model_config = ConfigDict(extra="forbid")

class SourceOutputSchema(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ImportOutputSchema(BaseModel):
    batch_id: int
    filename: str
    rows_total: int
    records_accepted: int
    issues_count: int

class GetImportsBatchSchema(BaseModel):
    id: int
    source_id: int
    filename: str
    file_uuid: str
    uploaded_at: datetime
    rows_total: int
    accepted: int
    rejected: int

    model_config = ConfigDict(from_attributes=True)

class GetImportsLogsSchema(BaseModel):
    row_number: int
    cells: list[str]
    status: str
    reject_reason: str | None

    model_config = ConfigDict(from_attributes=True)

class IssueRefSchema(BaseModel):
    batch_id: int
    row_number: int

    model_config = ConfigDict(from_attributes=True)

class GetImportsIssuesSchema(BaseModel):
    code: str
    severity: str
    message: str
    refs: list[IssueRefSchema]

    model_config = ConfigDict(from_attributes=True)


class ReconciliationInputSchema(BaseModel):
    batch_ids: list[int] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class ReconciliationOutputSchema(BaseModel):
    run_id: int
    status: str
    assets_total: int
    issues_total: int

class UserRegister(BaseModel):
    login: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


