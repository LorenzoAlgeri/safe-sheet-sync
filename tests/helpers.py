"""Test-only helpers. Nothing here is imported by the library."""
import copy

from safesync import Store


def record(key, **over):
    """A complete stored record, with every field filled."""
    base = {
        "card_no": key,
        "first_name": "Ada",
        "last_name": "Placeholder",
        "phone": "0000000001",
        "branch": "central",
        "membership": "adult",
        "tags": [],
        "notes": "",
        "loan_limit": 5,
    }
    base.update(over)
    return base


def make_store(*records):
    return Store(records={r["card_no"]: copy.deepcopy(r) for r in records})


def row(card_no="", **fields):
    """A sheet row as csv.DictReader would give it: every cell is text."""
    base = {
        "card_no": card_no,
        "first_name": "",
        "last_name": "",
        "phone": "",
        "branch": "",
        "membership": "",
        "tags": "",
    }
    base.update(fields)
    return base


def row_like(rec, **over):
    """The sheet row that matches a stored record exactly (no change expected)."""
    base = row(
        rec["card_no"],
        first_name=rec["first_name"],
        last_name=rec["last_name"],
        phone=rec["phone"],
        branch=rec["branch"],
        membership=rec["membership"],
        tags=";".join(rec["tags"]),
    )
    base.update(over)
    return base


def records_of(store):
    return copy.deepcopy(store.records)


def diff_records(before, after):
    """What really changed between two copies of the records, field by field."""
    created = sorted(k for k in after if k not in before)
    removed = sorted(k for k in before if k not in after)
    changed = {}
    for key in before:
        if key in after and before[key] != after[key]:
            changed[key] = {
                f: after[key][f]
                for f in after[key]
                if after[key][f] != before[key].get(f)
            }
    return {"created": created, "removed": removed, "changed": changed}


def naive_overwrite(store, rows):
    """The import that caused the incident: replace whole records with the sheet.

    It only exists here, to show the damage and to prove the history can undo it.
    """
    for r in rows:
        key = r["card_no"]
        if key in store.records:
            store.save_version(key)
        store.records[key] = {
            "card_no": key,
            "first_name": r["first_name"],
            "last_name": r["last_name"],
            "phone": r["phone"],
            "branch": r["branch"],
            "membership": r["membership"].lower(),
            "tags": [t for t in r["tags"].split(";") if t],
            "notes": "",
            "loan_limit": 5,
        }
