"""apply(): writes only what the plan declares, and keeps a version first."""
import copy

from helpers import diff_records, make_store, record, records_of, row, row_like

from safesync import apply, format_plan, plan


def test_apply_creates_and_updates_and_versions_only_the_updated_record():
    store = make_store(record("LB-0001", phone="0000000001"))
    sheet = [
        row_like(record("LB-0001"), phone="000 000 0101"),
        row("LB-0002", first_name="Ben", last_name="Sample", branch="north"),
    ]

    result = apply(plan(sheet, store), store)

    assert store.records["LB-0001"]["phone"] == "000 000 0101"
    assert store.records["LB-0002"]["first_name"] == "Ben"
    assert result["created"] == ["LB-0002"]
    assert result["updated"] == ["LB-0001"]
    assert list(store.versions) == ["LB-0001"]
    assert store.versions["LB-0001"][0]["version"] == 1
    assert store.versions["LB-0001"][0]["record"]["phone"] == "0000000001"


def test_apply_never_blanks_a_filled_field_even_if_a_plan_says_so():
    store = make_store(record("LB-0001", branch="north"))
    hand_made = {
        "creates": [],
        "updates": [
            {
                "key": "LB-0001",
                "label": "x",
                "changes": {"branch": {"from": "north", "to": ""}},
            }
        ],
        "unchanged": [],
        "absent": [],
        "skipped": [],
    }

    result = apply(hand_made, store)

    assert store.records["LB-0001"]["branch"] == "north"
    assert store.versions == {}
    assert result["updated"] == []
    assert result["skipped"][0]["reason"] == "would blank a filled field"


def test_apply_ignores_fields_the_sync_does_not_own():
    store = make_store(record("LB-0001", notes="prefers large print"))
    hand_made = {
        "creates": [],
        "updates": [
            {
                "key": "LB-0001",
                "label": "x",
                "changes": {"notes": {"from": "prefers large print", "to": "oops"}},
            }
        ],
        "unchanged": [],
        "absent": [],
        "skipped": [],
    }

    apply(hand_made, store)

    assert store.records["LB-0001"]["notes"] == "prefers large print"
    assert store.versions == {}


def test_apply_touches_nothing_the_plan_does_not_mention():
    store = make_store(record("LB-0001"), record("LB-0002"), record("LB-0003"))
    sheet = [row_like(record("LB-0001"), branch="north")]  # 0002 and 0003 absent
    before = records_of(store)

    apply(plan(sheet, store), store)

    assert store.records["LB-0002"] == before["LB-0002"]
    assert store.records["LB-0003"] == before["LB-0003"]
    assert "LB-0002" not in store.versions and "LB-0003" not in store.versions


def test_applying_the_same_plan_twice_has_no_extra_effect():
    store = make_store(record("LB-0001", phone="0000000001"))
    sheet = [
        row_like(record("LB-0001"), phone="000 000 0101"),
        row("LB-0002", first_name="Ben"),
    ]
    the_plan = plan(sheet, store)

    apply(the_plan, store)
    after_first = store.to_dict()
    second = apply(the_plan, store)

    assert store.to_dict() == after_first
    assert second["created"] == [] and second["updated"] == []
    assert len(store.versions["LB-0001"]) == 1


def test_stale_plan_does_not_overwrite_a_newer_hand_edit():
    store = make_store(record("LB-0001", phone="0000000001"))
    the_plan = plan([row_like(record("LB-0001"), phone="000 000 0101")], store)
    store.records["LB-0001"]["phone"] = "000 000 0777"  # someone edits meanwhile

    result = apply(the_plan, store)

    assert store.records["LB-0001"]["phone"] == "000 000 0777"
    assert result["updated"] == []
    assert "changed since the plan" in result["skipped"][0]["reason"]


def test_dry_run_and_real_write_agree():
    """The key rule: the printed plan and the real effect are the same thing."""
    existing = [
        record("LB-0001"),
        record("LB-0002", phone="0000000002"),
        record("LB-0003", branch="north"),
        record("LB-0009"),
    ]
    store = make_store(*existing)
    sheet = [
        row_like(existing[0]),
        row_like(existing[1], phone="000 000 0102"),
        row_like(existing[2], branch="central"),
        row("LB-0004", first_name="Dan", last_name="Demo", branch="north"),
        row(""),
    ]
    before = records_of(store)

    the_plan = plan(sheet, store)
    printed = format_plan(the_plan)
    assert records_of(store) == before  # the dry run wrote nothing

    apply(the_plan, store)
    observed = diff_records(before, records_of(store))

    assert observed["created"] == [c["key"] for c in the_plan["creates"]]
    assert observed["changed"] == {
        u["key"]: {f: c["to"] for f, c in u["changes"].items()}
        for u in the_plan["updates"]
    }
    assert observed["removed"] == []
    assert "phone: 0000000002 -> 000 000 0102" in printed
    assert "branch: north -> central" in printed
    assert "+ LB-0004" in printed
    # a plan made again from the same inputs still says the same thing
    assert plan(sheet, make_store(*existing)) == the_plan
    assert format_plan(plan(sheet, make_store(*existing))) == printed


def test_plan_after_apply_finds_nothing_left_to_do():
    store = make_store(record("LB-0001", phone="0000000001"))
    sheet = [
        row_like(record("LB-0001"), phone="000 000 0101"),
        row("LB-0002", first_name="Ben", branch="north"),
    ]
    apply(plan(sheet, store), store)

    again = plan(sheet, copy.deepcopy(store))

    assert again["creates"] == [] and again["updates"] == []
    assert sorted(again["unchanged"]) == ["LB-0001", "LB-0002"]
