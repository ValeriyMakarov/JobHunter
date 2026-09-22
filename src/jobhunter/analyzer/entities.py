from dataclasses import dataclass


@dataclass
class AnalyzedDataInfo:
    _vacancy_id: str
    is_suitable: bool = True
    vacancy_description: str = ""

    @property
    def vacancy_id(self):
        return self._vacancy_id

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, AnalyzedDataInfo):
            return NotImplemented
        return value.vacancy_id == self._vacancy_id

    def __hash__(self) -> int:
        return hash(self._vacancy_id)