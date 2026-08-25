from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    remember_me: bool = False

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("密码必须同时包含字母和数字")
        return value


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str
    quota_remaining: int

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class CreateCaseRequest(BaseModel):
    title: str = Field(min_length=5, max_length=500)
    subject: str
    course_name: str
    case_type: str = "决策型"
    difficulty: str = "中级"
    target_audience: str = "本科"
    target_words: int = Field(default=2800, ge=1500, le=5000)
    learning_objectives: list[str] = Field(min_length=1)
    workflow_template: str = "sequential_standard"
    class_hours: int | None = 2
    special_requirements: str | None = None


class ObjectiveSuggestionRequest(BaseModel):
    title: str = Field(min_length=5, max_length=500)
    subject: str
    course_name: str = Field(min_length=1, max_length=200)
    case_type: str = "决策型"
    difficulty: str = "中级"
    target_audience: str = "本科"
    variant: int = Field(default=0, ge=0, le=1000)


class ObjectiveSuggestionResponse(BaseModel):
    framework: str
    framework_name: str
    rationale: str
    objectives: list[str]


class CaseTaskOut(BaseModel):
    id: str
    title: str
    subject: str
    course_name: str
    case_type: str
    difficulty: str
    target_audience: str
    status: str
    workflow_template: str
    rubric_overall: float | None = None
    created_at: datetime | str
    updated_at: datetime | str

    model_config = {"from_attributes": True}


class PptOptions(BaseModel):
    theme: Literal["academic", "modern", "minimal"] = "academic"
    density: Literal["concise", "standard", "detailed"] = "standard"
    audience: Literal["student", "teacher"] = "teacher"
    mode: Literal["lecture", "workshop", "visual"] = "lecture"
    include_speaker_notes: bool = True


class PptOutlineRequest(PptOptions):
    pass


class ExportRequest(BaseModel):
    format: Literal["docx", "pdf", "pptx"]
    ppt_options: PptOptions | None = None


class ExportResponse(BaseModel):
    export_id: str
    format: str
    download_url: str
    filename: str
    version: int


class DashboardStatsOut(BaseModel):
    total_cases: int
    total_cases_delta: int
    finalized_count: int
    completion_rate: float
    running_count: int
    avg_rubric: float
    avg_rubric_delta: float
    estimated_hours_saved: int
    export_count: dict[str, int]
    avg_generation_minutes: float
    discussion_questions_total: int
    agent_regenerate_count: int
    quota_remaining: int
    subject_distribution: dict[str, int]
    status_distribution: dict[str, int]
    monthly_trend: list[dict[str, Any]]


class AgentConfigOut(BaseModel):
    agent_name: str
    version: str
    is_active: bool
    description: str | None = None


class AgentConfigUpdate(BaseModel):
    config_yaml: str
    activate: bool = True


# CasePackage JSON Schema（与前端 types/case.ts 对齐）
class CaseMeta(BaseModel):
    title: str
    subject: str
    course: str
    difficulty: str = "intermediate"
    case_type: str = "decision"
    fictional_disclaimer: str = "本案例为教学虚构情境，不代表任何真实企业或个人"


class LearningObjective(BaseModel):
    id: str | None = None
    level: str
    description: str
    assessment_hint: str | None = None


class DiscussionQuestion(BaseModel):
    level: str
    question: str
    teaching_intent: str | None = None


class CaseBody(BaseModel):
    background: str = ""
    narrative: str = ""
    decision_point: str = ""
    characters: list[dict[str, str]] = []


class InstructorGuide(BaseModel):
    teaching_flow: str = ""
    key_points: list[str] = []
    common_misconceptions: list[str] = []
    extension_reading: list[str] = []


class AlignmentRow(BaseModel):
    objective_id: str
    case_section: str
    activity: str
    assessment: str


class CaseQuality(BaseModel):
    rubric_scores: dict[str, float] = {}
    reviewer_summary: str = ""
    overall_score: float = 0.0


class VisualAsset(BaseModel):
    id: str
    title: str
    caption: str
    source_org: str
    source_page_url: str
    image_url: str | None = None
    preview_url: str
    published_at: str | None = None
    photographer: str | None = None
    section_hint: str | None = None
    rights_notice: str
    official: bool = True
    match_reasons: list[str] = []


class CasePackageSchema(BaseModel):
    meta: CaseMeta
    learning_objectives: list[LearningObjective]
    body: CaseBody
    discussion_questions: list[DiscussionQuestion]
    instructor_guide: InstructorGuide
    alignment_matrix: list[AlignmentRow]
    visual_assets: list[VisualAsset] = []
    material_research: dict[str, Any] | None = None
    quality: CaseQuality | None = None
