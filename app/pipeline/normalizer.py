from datetime import datetime, date
from difflib import get_close_matches

from app.domain.schemas import NormalizedRecord, Issue, IssueCode, Severity, RowRef
from app.rules.loader import Rules, normalize_key


def clean_key(key: str | None) -> str | None:
    if not key:
        return None
    key = "".join(key.split()).upper()
    return key

def clean_text(value: str | None) -> str | None:
    if not value:
        return None
    value = " ".join(value.split())
    return value

def suggest_status(raw: str, rules: Rules) -> str | None:
    key = normalize_key(raw)
    matches = get_close_matches(key, rules.statuses.keys(), n=1, cutoff=0.6)
    return rules.statuses[matches[0]] if matches else None

def parse_date(value: str) -> date | None:
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None

def normalize_row(data: dict, ref: RowRef, rules: Rules, raw: dict) -> tuple[NormalizedRecord, list[Issue]]:
    issues: list[Issue] = []

    inventory_number = clean_key(data.get("inventory_number"))
    serial_number = clean_key(data.get("serial_number"))
    name = clean_text(data.get("name"))
    type_raw = clean_text(data.get("asset_type"))

    manufacturer = clean_text(data.get("manufacturer"))
    model = clean_text(data.get("model"))
    specs = clean_text(data.get("specs"))

    responsible_person = clean_text(data.get("responsible_person"))
    location = clean_text(data.get("location"))

    for field, value in (("name", name), ("asset_type", type_raw),
                         ("inventory_number", inventory_number), ("location", location),
                         ("responsible_person", responsible_person)):
        if not value:
            issues.append(Issue(refs=[ref], code=IssueCode.MISSING_FIELD, severity=Severity.MEDIUM,
                                message=f"Поле {field} пустое", field=field))

    found = rules.asset_type(type_raw) if type_raw else None
    if not found:
        issues.append(Issue(refs=[ref], code=IssueCode.INVALID_ASSET_TYPE,
                            severity=Severity.MEDIUM, message=f"Оборудование типа {type_raw} не найдено в справочнике",
                            field="asset_type"))
    asset_type, category = found if found else (type_raw, None)

    status_raw = clean_text(data.get("status"))
    status = None
    if status_raw is None:
        issues.append(Issue(refs=[ref], code=IssueCode.MISSING_FIELD, severity=Severity.HIGH,
                            message="Поле status пустое", field="status"))
    else:
        status = rules.status(status_raw)
        if status is None:
            suggestion = suggest_status(status_raw, rules)
            message = f"Статус «{status_raw}» не распознан"
            if suggestion:
                message += f". Возможно, имелось в виду: {suggestion}?"
            issues.append(Issue(refs=[ref], code=IssueCode.INVALID_STATUS, severity=Severity.MEDIUM,
                                message=message,
                                field="status",
                                suggestion=suggestion))

    inv_num_pattern = rules.formats["inventory_number"]
    if inventory_number and not inv_num_pattern.match(inventory_number):
        issues.append(Issue(refs=[ref], code=IssueCode.BAD_FORMAT, severity=Severity.MEDIUM,
                            message=f"Инв. номер {inventory_number} не подходит по формату. Убедитесь в правильности написания инв. номера",
                            field="inventory_number"))

    ip_pattern = rules.formats["ip_address"]
    serial_num_pattern = rules.formats["serial_number"]
    if serial_number:
        if ip_pattern.match(serial_number):
            issues.append(Issue(refs=[ref], code=IssueCode.BAD_FORMAT, severity=Severity.MEDIUM,
                                message=f"В поле серийного номера указан IP-адрес: {serial_number}",
                                field="serial_number"))
        elif not serial_num_pattern.match(serial_number):
            issues.append(Issue(refs=[ref], code=IssueCode.BAD_FORMAT, severity=Severity.MEDIUM,
                                message=f"Серийный номер {serial_number} не подходит по формату. Убедитесь в правильности написания серийного номера",
                                field="serial_number"))


    raw_date = clean_text(data.get("commissioning_date"))
    commissioning_date = parse_date(raw_date) if raw_date else None
    if raw_date and commissioning_date is None:
        issues.append(Issue(refs=[ref], code=IssueCode.BAD_FORMAT, severity=Severity.LOW,
                            message=f"Дата «{raw_date}» не распознана", field="commissioning_date"))

    record = NormalizedRecord(ref=ref,
                              inventory_number=inventory_number,
                              serial_number=serial_number,
                              name=name,
                              asset_type=asset_type,
                              category=category,
                              manufacturer=manufacturer,
                              model=model,
                              specs=specs,
                              status=status,
                              status_raw=status_raw,
                              responsible_person=responsible_person,
                              location=location,
                              commissioning_date=commissioning_date,
                              raw=raw)

    return record, issues