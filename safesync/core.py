"""plan, apply and restore. Standard library only.

plan() decides everything and writes nothing. apply() does only what a plan
declares. The dry run and the real write share the same plan, so they cannot
disagree.
"""
import copy

KEY_FIELD = "card_no"
SYNCED_FIELDS = ("first_name", "last_name", "phone", "branch", "membership", "tags")
# Fields the sheet does not own. They get these values on creation and are never
# changed by a sync afterwards.
PROTECTED_DEFAULTS = {"notes": "", "loan_limit": 5}


def is_empty(value):
    return value is None or value == "" or value == []


def clean_cell(field, value):
    if field == "tags":
        parts = value.split(";") if isinstance(value, str) else list(value or [])
        tags = []
        for part in parts:
            tag = " ".join(str(part).split())
            if tag and tag not in tags:
                tags.append(tag)
        return tags
    text = " ".join(str(value or "").split())
    return text.lower() if field == "membership" else text


def clean_row(row):
    return {f: clean_cell(f, row.get(f)) for f in SYNCED_FIELDS}


def phone_digits(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[2:] if len(digits) > 10 and digits.startswith("39") else digits


def same(field, a, b):
    if field == "phone":
        return phone_digits(a) == phone_digits(b)
    if field == "tags":
        return list(a or []) == list(b or [])
    return (a or "") == (b or "")


def field_change(field, current, desired):
    """The change for one field, or None. A blank desired value never counts."""
    if is_empty(desired):
        return None
    if field == "tags":
        have = list(current or [])
        merged = have + [t for t in desired if t not in have]
        return None if merged == have else {"from": have, "to": merged}
    if same(field, current, desired):
        return None
    return {"from": current or "", "to": desired}


def new_record(key, cleaned):
    record = {KEY_FIELD: key}
    record.update(cleaned)
    record.update(copy.deepcopy(PROTECTED_DEFAULTS))
    return record


def plan(sheet_rows, store):
    result = {"creates": [], "updates": [], "unchanged": [], "absent": [], "skipped": []}
    rows_by_key = {}
    order = []
    for number, raw in enumerate(sheet_rows, start=1):
        key = " ".join(str(raw.get(KEY_FIELD) or "").split())
        if not key:
            result["skipped"].append({"row": number, "key": "", "reason": "no card number"})
            continue
        if key not in rows_by_key:
            rows_by_key[key] = []
            order.append(key)
        rows_by_key[key].append((number, clean_row(raw)))

    for key in order:
        entries = rows_by_key[key]
        first_number, cleaned = entries[0]
        if len(entries) > 1:
            if all(other == cleaned for _, other in entries[1:]):
                for number, _ in entries[1:]:
                    result["skipped"].append(
                        {
                            "row": number,
                            "key": key,
                            "reason": f"duplicate of data row {first_number}, same values",
                        }
                    )
            else:
                for number, _ in entries:
                    result["skipped"].append(
                        {
                            "row": number,
                            "key": key,
                            "reason": "conflicting duplicate rows, record left alone",
                        }
                    )
                continue

        current = store.records.get(key)
        if current is None:
            result["creates"].append({"key": key, "record": new_record(key, cleaned)})
            continue

        changes = {}
        for field in SYNCED_FIELDS:
            change = field_change(field, current.get(field), cleaned[field])
            if change:
                changes[field] = change
        if changes:
            label = " ".join(
                p for p in (current.get("first_name"), current.get("last_name")) if p
            )
            result["updates"].append({"key": key, "label": label, "changes": changes})
        else:
            result["unchanged"].append(key)

    result["absent"] = sorted(k for k in store.records if k not in rows_by_key)
    result["skipped"].sort(key=lambda s: s["row"])
    return result


def apply(the_plan, store):
    """Write what the plan declares, nothing more. Safe to run twice."""
    result = {"created": [], "updated": [], "skipped": []}

    for item in the_plan["creates"]:
        key = item["key"]
        if key in store.records:
            result["skipped"].append({"key": key, "field": "", "reason": "already exists"})
            continue
        store.records[key] = copy.deepcopy(item["record"])
        result["created"].append(key)

    for item in the_plan["updates"]:
        key = item["key"]
        current = store.records.get(key)
        if current is None:
            result["skipped"].append({"key": key, "field": "", "reason": "record not found"})
            continue
        to_write = {}
        for field, change in item["changes"].items():
            if field not in SYNCED_FIELDS:
                reason = "not a field the sync owns"
            elif is_empty(change["to"]) and not is_empty(current.get(field)):
                reason = "would blank a filled field"
            elif same(field, current.get(field), change["to"]):
                continue  # already applied
            elif not same(field, current.get(field), change["from"]):
                reason = "changed since the plan was made"
            else:
                to_write[field] = copy.deepcopy(change["to"])
                continue
            result["skipped"].append({"key": key, "field": field, "reason": reason})
        if to_write:
            store.save_version(key)
            current.update(to_write)
            result["updated"].append(key)
    return result


def restore(store, record_id, version):
    """Put a saved version back. The state it replaces is saved first."""
    history = store.versions.get(record_id)
    if not history or record_id not in store.records:
        raise ValueError(f"no history for record {record_id}")
    if not isinstance(version, int) or version < 1 or version > len(history):
        raise ValueError(f"no version {version} for record {record_id}")
    saved = copy.deepcopy(history[version - 1]["record"])
    store.save_version(record_id)
    store.records[record_id] = saved
    return copy.deepcopy(saved)
