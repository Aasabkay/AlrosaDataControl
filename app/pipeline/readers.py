import csv
import io
from datetime import datetime, date
from pathlib import Path
from typing import Iterator

from openpyxl import load_workbook


def decode_bytes(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1251"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Не удалось определить кодировку")

CANDIDATES = [";", ",", "\t", "|"]

def detect_delimiter(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            header = line
            break
    else:
        return ","

    counts = {d: header.count(d) for d in CANDIDATES}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","

def read_csv_rows(path: Path):
    text = decode_bytes(path.read_bytes())
    delimiter = detect_delimiter(text)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    for row in reader:
        row_number = reader.line_num
        cells = [cell.strip() for cell in row]
        if not any(cells):
            continue

        yield row_number, cells

def cell_to_str(cell) -> str:
    if cell is None:
        return ""

    if isinstance(cell, (datetime, date)):
        return cell.strftime("%d.%m.%Y")
    if isinstance(cell, float) and cell.is_integer():
        return str(int(cell))

    return str(cell).strip()

def read_xlsx_rows(path: Path):
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.active
        width = None
        for row_number, row in enumerate(ws.iter_rows(values_only=True), start=1):
            cells = [cell_to_str(value) for value in row]
            if not any(cells):
                continue
            if width is None:
                width = len(cells)
                while width and not cells[width - 1]:
                    width -= 1
            elif len(cells) < width:
                cells += [""] * (width - len(cells))

            yield row_number, cells
    finally:
        wb.close()

def read_rows(path: Path) -> Iterator[tuple[int, list[str]]]:
    readers = {
        ".csv": read_csv_rows,
        ".xlsx": read_xlsx_rows,
    }
    reader = readers.get(path.suffix.lower())
    if reader is None:
        raise ValueError(f"Неподдерживаемый формат файла: {path.suffix!r}")

    return reader(path)