from pydantic import BaseModel, Field


class DocumentAnalysis(BaseModel):
    document_type: str
    summary: str
    key_information: list[str] = Field(default_factory=list)
    important_dates: list[str] = Field(default_factory=list)
    amounts: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    inconsistencies: list[str] = Field(default_factory=list)

class DocumentComparison(BaseModel):
    summary: str
    similarities: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)
    conflicting_dates: list[str] = Field(default_factory=list)
    conflicting_amounts: list[str] = Field(default_factory=list)
    conflicting_information: list[str] = Field(default_factory=list)
