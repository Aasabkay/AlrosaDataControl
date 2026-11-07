from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, computed_field


class IssueCategory(StrEnum):
    EXCLUDED = "excluded"          # исключённые строки
    DUPLICATE = "duplicate"        # дубликаты
    MISSING_OR_STATUS = "missing"  # пропуски и статусы
    MISMATCH = "mismatch"          # расхождения между источниками

class IssueCode(StrEnum):
    # исключённые строки
    BAD_COLUMN_COUNT = "BAD_COLUMN_COUNT"
    PARENT_REJECTED = "PARENT_REJECTED"
    NAME_CONFLICT = "NAME_CONFLICT"
    INVENTORY_CONFLICT = "INVENTORY_CONFLICT"
    NO_PARENT = "NO_PARENT"
    # дубликаты
    DUP_IN_SOURCE = "DUP_IN_SOURCE"
    DUP_CROSS_SOURCE = "DUP_CROSS_SOURCE"
    # пропуски и статусы
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_STATUS = "INVALID_STATUS"
    BAD_FORMAT = "BAD_FORMAT"
    INVALID_ASSET_TYPE = "INVALID_ASSET_TYPE"
    # расхождения
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
    """Критичность ошибки"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class AssetCategory(StrEnum):
    """Список категорий оборудования"""
    ENDPOINT = "endpoint"        # оконечное: ПК, ноутбук, сервер
    NETWORK = "network"          # сетевое: коммутатор, маршрутизатор
    PERIPHERAL = "peripheral"    # периферия: монитор, принтер, сканер, клавиатура, мышь
    ADAPTER = "adapter"          # компонент в составе устройства: процессор, ОЗУ, сетевая карта


class MatchStatus(StrEnum):
    """Показывает итог сопоставления группы"""
    MATCHED = "matched"                  # есть пара в других источниках
    ONLY_IN_SOURCE = "only_in_source"    # запись есть только в одном источнике
    AMBIGUOUS = "ambiguous"              # несколько кандидатов, нужна ручная проверка


class MatchMethod(StrEnum):
    """Показывает, по какому признаку данные склеились (перечислены в порядке приоритета при сопоставлении)"""
    INVENTORY_NUMBER = "inventory_number"
    SERIAL_NUMBER = "serial_number"
    NAME = "name"                        # точное совпадение нормализованного названия (сетевого имени)
    FUZZY = "fuzzy"                      # производитель + модель + название через rapidfuzz

class RowRef(BaseModel):
    """Показывает откуда взялась запись"""
    source_id: int
    batch_id: int          # конкретная загрузка (import_batch)
    row_number: int        # номер строки в файле, считая с 1 (шапка = 1)

class NormalizedRecord(BaseModel):
    ref: RowRef

    # Ключи сопоставления (уже нормализованы: trim, верхний регистр, без пробелов внутри номера)
    inventory_number: str | None = None
    serial_number: str | None = None

    # Описание оборудования
    name: str | None = None
    asset_type: str | None = None
    category: AssetCategory | None = None  # None, если тип не найден в справочнике
    manufacturer: str | None = None
    model: str | None = None
    specs: str | None = None               # технические характеристики одной строкой, как в файле

    # Сравниваемые поля
    status: str | None = None          # каноническое значение из справочника; None, если не распознан
    status_raw: str | None = None      # как было в файле (для INVALID_STATUS и подсказки)
    responsible_person: str | None = None  # МОЛ, ФИО в формате «Фамилия И.О.»
    location: str | None = None
    commissioning_date: date | None = None

    # Исходные значения «как в файле»: для карточки актива и отладки
    raw: dict[str, str] = Field(default_factory=dict)

class AssetGroup(BaseModel):
    """Актив = группа записей из разных источников, признанных одной железкой."""
    asset_key: str                       # стабильный ключ группы, например инв. номер
    records: list[NormalizedRecord]      # Записи из разных групп про один аппарат
    match_status: MatchStatus
    match_method: MatchMethod | None = None
    match_score: float | None = None     # 0..100, только для FUZZY


class FieldValue(BaseModel):
    """Значение поля в конкретной строке. Список таких пар показывает, где и что расходится."""
    ref: RowRef
    value: str | None = None


class Issue(BaseModel):
    code: IssueCode
    severity: Severity
    message: str                         # человекочитаемый текст для отчёта

    # Где проблема (что-то из этого может быть пустым)
    refs: list[RowRef] = Field(default_factory=list)  # одна строка или несколько (дубли, расхождения)
    asset_key: str | None = None         # если проблема про актив, а не про строку
    field: str | None = None             # какое поле: "status", "location", ...

    # Значения по строкам. Для FIELD_MISMATCH, дублей и карточки с diff.
    values: list[FieldValue] = Field(default_factory=list)
    suggestion: str | None = None        # например ближайший статус из справочника

    @computed_field
    @property
    def category(self) -> IssueCategory:
        return CODE_CATEGORY[self.code]

