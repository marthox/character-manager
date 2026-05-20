from domain.models.base_class import BaseClass


class SheetTemplate(BaseClass):
    name: str
    system: str
    modules: list[str] = []
