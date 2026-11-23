"""restore(): go back to a saved version. Plus the incident, replayed."""
import pytest
from helpers import make_store, naive_overwrite, record, records_of, row, row_like

from safesync import apply, plan, restore


def test_restore_after_a_wrong_update_brings_the_old_record_back():
    original = record("LB-0001", phone="0000000001")
    store = make_store(original)
    wrong_sheet = [row_like(original, phone="000 000 9999")]
    apply(plan(wrong_sheet, store), store)
    assert store.records["LB-0001"]["phone"] == "000 000 9999"

    restored = restore(store, "LB-0001", 1)

    assert store.records["LB-0001"] == original
    assert restored == original


def test_restore_saves_the_current_state_first_so_it_can_be_undone():
    original = record("LB-0001", phone="0000000001")
    store = make_store(original)
    apply(plan([row_like(original, phone="000 000 9999")], store), store)

    restore(store, "LB-0001", 1)
    assert [v["version"] for v in store.versions["LB-0001"]] == [1, 2]
    assert store.versions["LB-0001"][1]["record"]["phone"] == "000 000 9999"

    restore(store, "LB-0001", 2)
    assert store.records["LB-0001"]["phone"] == "000 000 9999"


def test_restore_leaves_old_versions_unchanged():
    original = record("LB-0001", phone="0000000001")
    store = make_store(original)
    apply(plan([row_like(original, phone="000 000 9999")], store), store)
    first_version = dict(store.versions["LB-0001"][0]["record"])

    restore(store, "LB-0001", 1)

    assert store.versions["LB-0001"][0]["record"] == first_version


def test_restore_unknown_version_or_record_raises():
    original = record("LB-0001")
    store = make_store(original)
    apply(plan([row_like(original, branch="north")], store), store)

    with pytest.raises(ValueError, match="no version 5"):
        restore(store, "LB-0001", 5)
    with pytest.raises(ValueError, match="no version 0"):
        restore(store, "LB-0001", 0)
    with pytest.raises(ValueError, match="no history"):
        restore(store, "LB-0404", 1)


def _six_existing_records_with_hand_set_fields():
    return [
        record(
            f"LB-000{n}",
            phone=f"000000000{n}",
            branch="north",
            notes=f"hand note {n}",
            loan_limit=8,
            tags=["staff-pick"],
        )
        for n in range(1, 7)
    ]


def _sheet_that_overlaps_the_store(existing):
    rows = [
        row_like(r, branch="central", phone="" if r["card_no"].endswith("3") else r["phone"])
        for r in existing
    ]
    rows += [row("LB-0007", first_name="Gus"), row("LB-0008", first_name="Hana")]
    return rows


def test_incident_dry_run_lists_every_existing_record_before_any_write():
    existing = _six_existing_records_with_hand_set_fields()
    store = make_store(*existing)
    sheet = _sheet_that_overlaps_the_store(existing)
    before = records_of(store)

    the_plan = plan(sheet, store)

    # The dry run already shows that 6 existing records would be touched.
    assert [u["key"] for u in the_plan["updates"]] == [r["card_no"] for r in existing]
    assert [c["key"] for c in the_plan["creates"]] == ["LB-0007", "LB-0008"]
    # It shows exactly which fields, and none of them is a hand-set one.
    for update in the_plan["updates"]:
        assert set(update["changes"]) == {"branch"}
    # The blank phone cell of LB-0003 is not offered as a change.
    # And nothing has been written yet.
    assert records_of(store) == before
    assert store.versions == {}


def test_incident_non_destructive_apply_keeps_the_hand_set_fields():
    existing = _six_existing_records_with_hand_set_fields()
    store = make_store(*existing)

    apply(plan(_sheet_that_overlaps_the_store(existing), store), store)

    for n in range(1, 7):
        rec = store.records[f"LB-000{n}"]
        assert rec["notes"] == f"hand note {n}"
        assert rec["loan_limit"] == 8
        assert rec["tags"] == ["staff-pick"]
        assert rec["branch"] == "central"
    assert store.records["LB-0003"]["phone"] == "0000000003"


def test_incident_replayed_the_naive_overwrite_loses_data_and_history_recovers_it():
    existing = _six_existing_records_with_hand_set_fields()
    store = make_store(*existing)
    sheet = _sheet_that_overlaps_the_store(existing)

    naive_overwrite(store, sheet)

    assert store.records["LB-0001"]["notes"] == ""  # the damage
    assert store.records["LB-0003"]["phone"] == ""
    for rec in existing:
        restore(store, rec["card_no"], 1)
    for rec in existing:
        assert store.records[rec["card_no"]] == rec  # nothing was lost
