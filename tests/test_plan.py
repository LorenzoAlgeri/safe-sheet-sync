"""plan(): the dry run. It decides everything and writes nothing."""
from helpers import make_store, record, records_of, row, row_like

from safesync import plan


def test_new_record_is_planned_as_create():
    store = make_store()
    sheet = [
        row(
            "LB-0001",
            first_name="Ada",
            last_name="Placeholder",
            phone="+39 000 000 0001",
            branch="central",
            membership="ADULT",
            tags="poetry;history",
        )
    ]

    result = plan(sheet, store)

    assert [c["key"] for c in result["creates"]] == ["LB-0001"]
    created = result["creates"][0]["record"]
    assert created["membership"] == "adult"
    assert created["tags"] == ["poetry", "history"]
    assert created["notes"] == "" and created["loan_limit"] == 5
    assert result["updates"] == [] and result["unchanged"] == []


def test_existing_record_with_changed_field_is_planned_as_update():
    store = make_store(record("LB-0001", phone="0000000001"))
    sheet = [row_like(record("LB-0001"), phone="000 000 0101")]

    result = plan(sheet, store)

    assert result["creates"] == []
    assert len(result["updates"]) == 1
    assert result["updates"][0]["key"] == "LB-0001"
    assert result["updates"][0]["changes"] == {
        "phone": {"from": "0000000001", "to": "000 000 0101"}
    }


def test_blank_cell_in_sheet_does_not_erase_existing_value():
    store = make_store(record("LB-0001", branch="north"))
    sheet = [row_like(record("LB-0001"), branch="")]

    result = plan(sheet, store)

    assert result["updates"] == []
    assert result["unchanged"] == ["LB-0001"]


def test_filled_cell_fills_a_blank_field():
    store = make_store(record("LB-0001", phone=""))
    sheet = [row_like(record("LB-0001"), phone="000 000 0001")]

    result = plan(sheet, store)

    assert result["updates"][0]["changes"] == {
        "phone": {"from": "", "to": "000 000 0001"}
    }


def test_same_phone_written_another_way_is_not_a_change():
    store = make_store(record("LB-0001", phone="0000000001"))
    sheet = [row_like(record("LB-0001"), phone="+39 000 000 0001")]

    result = plan(sheet, store)

    assert result["updates"] == []
    assert result["unchanged"] == ["LB-0001"]


def test_membership_in_capitals_matches_the_stored_lowercase_value():
    store = make_store(record("LB-0001", membership="adult"))
    sheet = [row_like(record("LB-0001"), membership="ADULT")]

    assert plan(sheet, store)["updates"] == []


def test_duplicate_row_with_same_values_keeps_the_first_and_reports_the_second():
    store = make_store()
    same = row("LB-0001", first_name="Ada", last_name="Placeholder", branch="central")
    result = plan([same, dict(same)], store)

    assert [c["key"] for c in result["creates"]] == ["LB-0001"]
    assert result["skipped"] == [
        {
            "row": 2,
            "key": "LB-0001",
            "reason": "duplicate of data row 1, same values",
        }
    ]


def test_duplicate_rows_that_disagree_leave_the_record_alone():
    store = make_store(record("LB-0001", branch="north"))
    first = row_like(record("LB-0001"), branch="central")
    second = row_like(record("LB-0001"), branch="riverside")

    result = plan([first, second], store)

    assert result["creates"] == [] and result["updates"] == []
    assert result["unchanged"] == []
    assert [s["row"] for s in result["skipped"]] == [1, 2]
    assert all("conflicting" in s["reason"] for s in result["skipped"])
    assert result["absent"] == []


def test_row_without_card_number_is_skipped_with_its_row_number():
    store = make_store()
    sheet = [row("LB-0001", first_name="Ada"), row("", first_name="Ghost")]

    result = plan(sheet, store)

    assert [c["key"] for c in result["creates"]] == ["LB-0001"]
    assert result["skipped"] == [{"row": 2, "key": "", "reason": "no card number"}]


def test_columns_the_sheet_does_not_own_are_ignored():
    store = make_store(record("LB-0001", notes="prefers large print", loan_limit=9))
    existing = row_like(record("LB-0001"), notes="", loan_limit="1")
    brand_new = row("LB-0002", first_name="Ben", notes="from the sheet", loan_limit="1")

    result = plan([existing, brand_new], store)

    assert result["updates"] == []
    assert result["creates"][0]["record"]["notes"] == ""
    assert result["creates"][0]["record"]["loan_limit"] == 5


def test_record_missing_from_sheet_is_reported_and_nothing_else():
    store = make_store(record("LB-0001"), record("LB-0002"))
    sheet = [row_like(record("LB-0001"))]

    result = plan(sheet, store)

    assert result["absent"] == ["LB-0002"]
    assert result["creates"] == [] and result["updates"] == []


def test_tags_added_by_hand_are_kept_and_sheet_tags_are_added():
    store = make_store(record("LB-0001", tags=["staff-pick"]))
    sheet = [row_like(record("LB-0001"), tags="poetry;history")]

    result = plan(sheet, store)

    assert result["updates"][0]["changes"] == {
        "tags": {
            "from": ["staff-pick"],
            "to": ["staff-pick", "poetry", "history"],
        }
    }


def test_tags_already_present_are_not_a_change():
    store = make_store(record("LB-0001", tags=["poetry", "staff-pick"]))
    sheet = [row_like(record("LB-0001"), tags="poetry")]

    assert plan(sheet, store)["updates"] == []


def test_plan_does_not_write_to_the_store():
    store = make_store(record("LB-0001", phone="0000000001"), record("LB-0002"))
    sheet = [
        row_like(record("LB-0001"), phone="000 000 0101"),
        row("LB-0003", first_name="Cora"),
    ]
    before = records_of(store)

    plan(sheet, store)

    assert records_of(store) == before
    assert store.versions == {}


def test_plan_is_deterministic():
    store = make_store(record("LB-0001"), record("LB-0002"))
    sheet = [
        row_like(record("LB-0001"), branch="north"),
        row("LB-0003", first_name="Cora"),
        row(""),
    ]

    assert plan(sheet, store) == plan(sheet, store)
