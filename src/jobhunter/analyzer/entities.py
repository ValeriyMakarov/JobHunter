from dataclasses import dataclass


@dataclass
class AnalyzedDataInfo:
    vacancy_id: str
    is_suitable: bool = True
    vacancy_description: str = ""
