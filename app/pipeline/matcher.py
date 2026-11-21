from rapidfuzz import fuzz

from app.domain.schemas import AssetGroup, MatchMethod, MatchStatus, NormalizedRecord

# Насколько похожими должны быть подписи, чтобы склеить записи без номеров.
FUZZY_SCORE_CUTOFF = 85

# Если два кандидата отличаются меньше чем на столько баллов — это неоднозначность.
AMBIGUITY_DELTA = 5


def _determine_status(records: list[NormalizedRecord]) -> MatchStatus:
    unique_sources = {r.ref.source_id for r in records}
    return MatchStatus.MATCHED if len(unique_sources) > 1 else MatchStatus.ONLY_IN_SOURCE


def _group_by_key(
    records: list[NormalizedRecord],
    key_func,
    method: MatchMethod,
) -> tuple[list[AssetGroup], list[NormalizedRecord]]:
    """Группирует записи по ключу, записи без ключа возвращает отдельно."""
    buckets: dict[str, list[NormalizedRecord]] = {}
    leftovers: list[NormalizedRecord] = []

    for record in records:
        key = key_func(record)
        if key is None:
            leftovers.append(record)
        else:
            buckets.setdefault(key, []).append(record)

    groups = [
        AssetGroup(
            asset_key=key,
            records=group_records,
            match_status=_determine_status(group_records),
            match_method=method,
        )
        for key, group_records in buckets.items()
    ]
    return groups, leftovers


def _signature(group: AssetGroup) -> str | None:
    """Подпись для нечёткого сравнения: производитель + модель + название."""
    record = next((r for r in group.records if r.name), None)
    if record is None:
        return None

    parts = [record.manufacturer, record.model, record.name]
    signature = " ".join(part for part in parts if part)
    return signature.casefold()


def _merge_similar_names(groups: list[AssetGroup]) -> list[AssetGroup]:
    """Склеивает группы с похожими названиями, помечает неоднозначные.

    Работает только с группами, у которых нет инвентарного и серийного номеров:
    если номер есть, он уже решил, что это за актив, и гадать не нужно.
    """
    candidates = [g for g in groups if g.match_method == MatchMethod.NAME]
    others = [g for g in groups if g.match_method != MatchMethod.NAME]

    merged: list[AssetGroup] = []
    pending = list(candidates)

    while pending:
        current = pending.pop(0)
        current_signature = _signature(current)

        scored = []
        if current_signature:
            for other in pending:
                other_signature = _signature(other)
                if other_signature:
                    score = fuzz.WRatio(current_signature, other_signature)
                    scored.append((score, other))

        scored.sort(key=lambda pair: pair[0], reverse=True)

        if not scored or scored[0][0] < FUZZY_SCORE_CUTOFF:
            merged.append(current)
            continue

        best_score, best = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0

        if len(scored) > 1 and second_score >= FUZZY_SCORE_CUTOFF and best_score - second_score < AMBIGUITY_DELTA:
            current.match_status = MatchStatus.AMBIGUOUS
            current.match_method = MatchMethod.FUZZY
            current.match_score = best_score
            merged.append(current)
            continue

        current.records.extend(best.records)
        current.match_status = _determine_status(current.records)
        current.match_method = MatchMethod.FUZZY
        current.match_score = best_score
        pending.remove(best)
        merged.append(current)

    return [*others, *merged]


def match_records(records: list[NormalizedRecord]) -> list[AssetGroup]:
    """Склеивает записи в активы по ключам: инв. номер → серийный → название → fuzzy."""
    groups, leftovers = _group_by_key(
        records, lambda r: r.inventory_number, MatchMethod.INVENTORY_NUMBER
    )
    serial_groups, leftovers = _group_by_key(
        leftovers, lambda r: r.serial_number, MatchMethod.SERIAL_NUMBER
    )
    name_groups, leftovers = _group_by_key(
        leftovers, lambda r: r.name, MatchMethod.NAME
    )

    groups = [*groups, *serial_groups, *name_groups]
    groups = _merge_similar_names(groups)

    for record in leftovers:
        groups.append(
            AssetGroup(
                asset_key="UNKNOWN",
                records=[record],
                match_status=MatchStatus.ONLY_IN_SOURCE,
            )
        )

    return groups
