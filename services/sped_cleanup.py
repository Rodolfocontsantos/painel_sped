from collections import Counter, defaultdict
from dataclasses import dataclass


FIELDS_0200 = (
    "COD_ITEM",
    "DESCR_ITEM",
    "COD_BARRA",
    "COD_ANT_ITEM",
    "UNID_INV",
    "TIPO_ITEM",
    "COD_NCM",
    "EX_IPI",
    "COD_GEN",
    "COD_LST",
    "ALIQ_ICMS",
    "CEST",
)

MANDATORY_0200_POSITIONS = (1, 4, 5)  # DESCR_ITEM, UNID_INV e TIPO_ITEM
SUBORDINATE_0200_RECORDS = {"0205", "0206", "0210", "0220", "0221"}


@dataclass(frozen=True)
class Duplicate0200Group:
    cod_item: str
    kept_index: int
    removed_indices: tuple[int, ...]
    line_numbers: tuple[int, ...]
    conflicting_fields: tuple[str, ...]
    requires_manual_review: bool


@dataclass(frozen=True)
class Duplicate0200Analysis:
    groups: tuple[Duplicate0200Group, ...]

    @property
    def duplicate_count(self):
        return sum(len(group.line_numbers) - 1 for group in self.groups)

    @property
    def removable_count(self):
        return sum(len(group.removed_indices) for group in self.groups)

    @property
    def protected_group_count(self):
        return sum(group.requires_manual_review for group in self.groups)

    @property
    def conflicting_group_count(self):
        return sum(bool(group.conflicting_fields) for group in self.groups)


@dataclass(frozen=True)
class CleanupResult:
    corpo_sped: list[str]
    assinatura: list[str]
    removed_count: int


def _record_code(line):
    parts = line.split("|")
    if line.startswith("|") and len(parts) > 2:
        return parts[1]
    return ""


def _data_fields(line):
    parts = line.split("|")
    end = -1 if parts and parts[-1] == "" else len(parts)
    return parts[2:end]


def _completeness_score(index, fields):
    mandatory_filled = sum(
        position < len(fields) and bool(fields[position].strip())
        for position in MANDATORY_0200_POSITIONS
    )
    filled_fields = sum(bool(value.strip()) for value in fields[1:])
    content_length = sum(len(value.strip()) for value in fields[1:])
    return mandatory_filled, filled_fields, content_length, -index


def _conflicting_fields(occurrences):
    max_fields = max(len(fields) for _, _, fields in occurrences)
    conflicts = []
    for position in range(1, max_fields):
        values = {
            fields[position].strip() if position < len(fields) else ""
            for _, _, fields in occurrences
        }
        if len(values) > 1:
            name = FIELDS_0200[position] if position < len(FIELDS_0200) else f"CAMPO_{position + 2}"
            conflicts.append(name)
    return tuple(conflicts)


def _0200_indices_with_children(corpo_sped):
    indices_with_children = set()
    current_0200_index = None

    for index, line in enumerate(corpo_sped):
        record = _record_code(line)
        if record == "0200":
            current_0200_index = index
        elif record in SUBORDINATE_0200_RECORDS and current_0200_index is not None:
            indices_with_children.add(current_0200_index)
        elif record:
            current_0200_index = None

    return indices_with_children


def analyze_0200_duplicates(corpo_sped):
    occurrences_by_item = defaultdict(list)
    indices_with_children = _0200_indices_with_children(corpo_sped)

    for index, line in enumerate(corpo_sped):
        if _record_code(line) != "0200":
            continue
        fields = _data_fields(line)
        if not fields or not fields[0].strip():
            continue
        occurrences_by_item[fields[0].strip()].append((index, line, fields))

    groups = []
    for cod_item, occurrences in occurrences_by_item.items():
        if len(occurrences) < 2:
            continue

        occurrences_with_children = [
            occurrence
            for occurrence in occurrences
            if occurrence[0] in indices_with_children
        ]
        requires_manual_review = len(occurrences_with_children) > 1

        if len(occurrences_with_children) == 1:
            kept = occurrences_with_children[0]
        else:
            kept = max(
                occurrences,
                key=lambda occurrence: _completeness_score(
                    occurrence[0], occurrence[2]
                ),
            )

        removed_indices = ()
        if not requires_manual_review:
            removed_indices = tuple(
                occurrence[0]
                for occurrence in occurrences
                if occurrence[0] != kept[0]
            )
        groups.append(
            Duplicate0200Group(
                cod_item=cod_item,
                kept_index=kept[0],
                removed_indices=removed_indices,
                line_numbers=tuple(occurrence[0] + 1 for occurrence in occurrences),
                conflicting_fields=_conflicting_fields(occurrences),
                requires_manual_review=requires_manual_review,
            )
        )

    return Duplicate0200Analysis(groups=tuple(groups))


def count_records(corpo_sped, record_code):
    return sum(_record_code(line) == record_code for line in corpo_sped)


def _replace_field(line, field_index, value):
    parts = line.split("|")
    if field_index >= len(parts):
        return line
    parts[field_index] = str(value)
    return "|".join(parts)


def _remove_obsolete_9900_entries(corpo_sped, assinatura, removed_record_codes):
    all_lines = corpo_sped + assinatura
    counts = Counter(_record_code(line) for line in all_lines)
    updated_signature = []

    for line in assinatura:
        if _record_code(line) == "9900":
            parts = line.split("|")
            target = parts[2] if len(parts) > 2 else ""
            if target in removed_record_codes and counts[target] == 0:
                continue
        updated_signature.append(line)

    return updated_signature


def _recalculate_block_closings(lines):
    block_starts = {}
    file_end_index = next(
        (
            index
            for index, line in reversed(list(enumerate(lines)))
            if _record_code(line) == "9999"
        ),
        None,
    )

    for index, line in enumerate(lines):
        record = _record_code(line)
        if record == "0000":
            block_starts["0"] = index
        elif (
            len(record) == 4
            and record.endswith("001")
            and record[0] != "0"
        ):
            block_starts[record[0]] = index

        if len(record) == 4 and record.endswith("990") and record[0] in block_starts:
            block_end_index = index
            if record == "9990" and file_end_index is not None:
                # O QTD_LIN_9 inclui todos os registros de 9001 até 9999.
                block_end_index = file_end_index
            block_count = block_end_index - block_starts[record[0]] + 1
            lines[index] = _replace_field(line, 2, block_count)


def recalculate_sped_totals(corpo_sped, assinatura, removed_record_codes=()):
    updated_body = list(corpo_sped)
    updated_signature = _remove_obsolete_9900_entries(
        updated_body,
        list(assinatura),
        set(removed_record_codes),
    )
    body_length = len(updated_body)
    all_lines = updated_body + updated_signature

    _recalculate_block_closings(all_lines)

    record_counts = Counter(_record_code(line) for line in all_lines)
    for index, line in enumerate(all_lines):
        if _record_code(line) != "9900":
            continue
        parts = line.split("|")
        target = parts[2] if len(parts) > 2 else ""
        all_lines[index] = _replace_field(line, 3, record_counts[target])

    for index, line in enumerate(all_lines):
        if _record_code(line) == "9999":
            all_lines[index] = _replace_field(line, 2, len(all_lines))

    return all_lines[:body_length], all_lines[body_length:]


def remove_0200_duplicates(corpo_sped, assinatura):
    analysis = analyze_0200_duplicates(corpo_sped)
    indices_to_remove = {
        index
        for group in analysis.groups
        for index in group.removed_indices
    }
    updated_body = [
        line
        for index, line in enumerate(corpo_sped)
        if index not in indices_to_remove
    ]

    updated_body, updated_signature = recalculate_sped_totals(updated_body, assinatura)
    return CleanupResult(updated_body, updated_signature, len(indices_to_remove))


def remove_c101_records(corpo_sped, assinatura):
    updated_body = [line for line in corpo_sped if _record_code(line) != "C101"]
    removed_count = len(corpo_sped) - len(updated_body)
    updated_body, updated_signature = recalculate_sped_totals(
        updated_body,
        assinatura,
        removed_record_codes={"C101"},
    )
    return CleanupResult(updated_body, updated_signature, removed_count)
