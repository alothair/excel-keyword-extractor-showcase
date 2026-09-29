"""Bounded readers for CSV and the text portion of XLSX workbooks."""

from __future__ import annotations

import csv
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_EXPANDED_BYTES = 50 * 1024 * 1024
NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
CELL_REF = re.compile(r"([A-Z]+)")


class WorkbookError(ValueError):
    """Raised when spreadsheet input is unsupported or malformed."""


def _check_size(path: Path) -> None:
    if not path.is_file():
        raise WorkbookError(f"input file not found: {path}")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise WorkbookError("input exceeds the 20 MiB safety limit")


def _column_index(reference: str) -> int:
    match = CELL_REF.match(reference)
    if not match:
        raise WorkbookError(f"invalid cell reference: {reference}")
    value = 0
    for character in match.group(1):
        value = value * 26 + ord(character) - 64
    return value - 1


def read_rows(path: str | Path) -> list[dict[str, str]]:
    source = Path(path)
    _check_size(source)
    if source.suffix.casefold() == ".csv":
        return _read_csv(source)
    if source.suffix.casefold() == ".xlsx":
        return _read_xlsx(source)
    raise WorkbookError("input must be a .csv or .xlsx file")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise WorkbookError("CSV input needs a header row")
        return [{key: value or "" for key, value in row.items() if key is not None} for row in reader]


def _xml(archive: zipfile.ZipFile, name: str) -> ET.Element:
    try:
        return ET.fromstring(archive.read(name))
    except (KeyError, ET.ParseError) as error:
        raise WorkbookError(f"invalid XLSX structure: {name}") from error


def _read_xlsx(path: Path) -> list[dict[str, str]]:
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as error:
        raise WorkbookError("invalid XLSX archive") from error
    with archive:
        if sum(item.file_size for item in archive.infolist()) > MAX_EXPANDED_BYTES:
            raise WorkbookError("expanded XLSX content exceeds the 50 MiB safety limit")
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = _xml(archive, "xl/sharedStrings.xml")
            shared = ["".join(node.text or "" for node in item.findall(".//x:t", NS)) for item in root.findall("x:si", NS)]
        workbook = _xml(archive, "xl/workbook.xml")
        first_sheet = workbook.find(".//x:sheet", NS)
        if first_sheet is None:
            raise WorkbookError("XLSX contains no worksheets")
        relation_id = first_sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        relations = _xml(archive, "xl/_rels/workbook.xml.rels")
        target = next((item.attrib.get("Target") for item in relations.findall("r:Relationship", REL_NS) if item.attrib.get("Id") == relation_id), None)
        if not target:
            raise WorkbookError("cannot locate the first worksheet")
        sheet_name = "xl/" + target.lstrip("/").removeprefix("xl/")
        sheet = _xml(archive, sheet_name)
        matrix: list[list[str]] = []
        for row in sheet.findall(".//x:sheetData/x:row", NS):
            values: list[str] = []
            for cell in row.findall("x:c", NS):
                index = _column_index(cell.attrib.get("r", ""))
                while len(values) <= index:
                    values.append("")
                kind = cell.attrib.get("t")
                raw = cell.findtext("x:v", default="", namespaces=NS)
                if kind == "s" and raw:
                    try:
                        values[index] = shared[int(raw)]
                    except (IndexError, ValueError) as error:
                        raise WorkbookError("invalid shared string reference") from error
                elif kind == "inlineStr":
                    values[index] = "".join(node.text or "" for node in cell.findall(".//x:t", NS))
                else:
                    values[index] = raw
            matrix.append(values)
    if not matrix or not any(matrix[0]):
        raise WorkbookError("XLSX first row must contain headers")
    headers = [value.strip() or f"column_{index + 1}" for index, value in enumerate(matrix[0])]
    return [{header: row[index] if index < len(row) else "" for index, header in enumerate(headers)} for row in matrix[1:]]
