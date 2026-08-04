from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class ApplicationData(BaseModel):
    work_email: str = Field(
        description="email address app will use for application responses and login messages"
    )
    city_index: int
    linkedin_link: str = Field(description="https://www.linkedin.com/in/your_name/")


class OtherQAFilters(BaseModel):
    location: str = Field(description="country name, use params from site")
    sort_by: str = Field(default="Most recent")
    job_type: str = Field(default="Full-time", description="use params from site")
    work_place: str = Field(default="Remote", description="use params from site")
    job_function: list[str] = Field(
        default_factory=lambda: ["Information Technology", "Engineering", "Quality Assurance"],
        description="use params from site"
    )


class Linkedin(BaseModel):
    qa_filter: str = Field(description="job keys, what you are looking for")
    other_qa_filters: OtherQAFilters


class Sites(BaseModel):
    linkedin: Linkedin | None = None


class Config(BaseModel):
    sites: Sites
    application_data: ApplicationData = Field(description="job application details")
    application_data_file: Path = Field(description="full path/file.xlsx")
    candidate_info_file_name: str | None = Field(
        description="file name from 'settings/candidate_info' folder with info about you"
    )

    @model_validator(mode="after")
    def validate_minimum_one_site_exists(self):
        if not self.sites.model_dump(exclude_none=True):
            raise ValueError(
                "At least one site configuration is required."
            )
        return self
