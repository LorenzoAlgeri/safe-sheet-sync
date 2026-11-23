"""The command line: the same plan is printed with and without --dry-run."""
import json
import shutil
from pathlib import Path

import pytest

from sync import main

EXAMPLE = Path(__file__).resolve().parent.parent / "example"
SPLIT = "\n== result ==\n"


def run(capsys, *args):
    code = main([str(a) for a in args])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_dry_run_prints_the_plan_and_writes_nothing(tmp_path, capsys):
    store_path = tmp_path / "store.json"

    code, out, _ = run(capsys, "--dry-run", EXAMPLE / "members.csv", "--store", store_path)

    assert code == 0
    assert "PLAN: 12 to create" in out
    assert "Dry run" in out
    assert not store_path.exists()


def test_dry_run_leaves_an_existing_store_byte_for_byte_unchanged(tmp_path, capsys):
    store_path = tmp_path / "store.json"
    run(capsys, EXAMPLE / "members.csv", "--store", store_path)
    before = store_path.read_bytes()

    run(capsys, "--dry-run", EXAMPLE / "members_march.csv", "--store", store_path)

    assert store_path.read_bytes() == before


def test_real_run_applies_and_a_second_run_changes_nothing(tmp_path, capsys):
    store_path = tmp_path / "store.json"

    code, out, _ = run(capsys, EXAMPLE / "members.csv", "--store", store_path)
    assert code == 0 and "Applied: 12 created, 0 updated" in out
    first = store_path.read_bytes()

    code, out, _ = run(capsys, EXAMPLE / "members.csv", "--store", store_path)
    assert code == 0
    assert "PLAN: 0 to create, 0 to update, 12 unchanged" in out
    assert "Nothing to change." in out
    assert store_path.read_bytes() == first


def test_printed_plan_is_identical_with_and_without_dry_run(tmp_path, capsys):
    store_path = tmp_path / "store.json"
    run(capsys, EXAMPLE / "members.csv", "--store", store_path)
    copy_path = tmp_path / "copy.json"
    shutil.copy(store_path, copy_path)

    _, dry, _ = run(capsys, "--dry-run", EXAMPLE / "members_march.csv", "--store", store_path)
    _, real, _ = run(capsys, EXAMPLE / "members_march.csv", "--store", copy_path)

    assert dry.split(SPLIT)[0] == real.split(SPLIT)[0]


def test_march_sheet_shows_the_safety_rules_at_work(tmp_path, capsys):
    store_path = tmp_path / "store.json"
    run(capsys, EXAMPLE / "members.csv", "--store", store_path)
    data = json.loads(store_path.read_text(encoding="utf-8"))
    data["records"]["LB-0004"]["notes"] = "added by a librarian"
    store_path.write_text(json.dumps(data), encoding="utf-8")

    _, out, _ = run(capsys, EXAMPLE / "members_march.csv", "--store", store_path)

    after = json.loads(store_path.read_text(encoding="utf-8"))["records"]
    assert after["LB-0004"]["notes"] == "added by a librarian"
    assert after["LB-0004"]["phone"] == "0000000004"  # blank cell did not erase
    assert after["LB-0002"]["phone"] == "000 000 0102"
    assert after["LB-0013"]["first_name"] == "Mona"
    assert "LB-0010" in out and "conflicting" in out
    assert "no card number" in out
    assert "LB-0012" in out  # reported as missing from the sheet
    assert "LB-0012" in after  # and not deleted


def test_history_and_restore(tmp_path, capsys):
    store_path = tmp_path / "store.json"
    run(capsys, EXAMPLE / "members.csv", "--store", store_path)
    run(capsys, EXAMPLE / "members_march.csv", "--store", store_path)

    code, out, _ = run(capsys, "--history", "LB-0002", "--store", store_path)
    assert code == 0 and "version 1" in out and "000 000 0002" in out

    code, out, _ = run(capsys, "--restore", "LB-0002", "1", "--store", store_path)
    assert code == 0 and "Restored LB-0002 to version 1" in out
    after = json.loads(store_path.read_text(encoding="utf-8"))["records"]
    assert after["LB-0002"]["phone"] == "000 000 0002"


def test_errors_exit_with_code_2_and_a_message(tmp_path, capsys):
    code, _, err = run(capsys, tmp_path / "missing.csv", "--store", tmp_path / "s.json")
    assert code == 2 and "not found" in err

    code, _, err = run(capsys, "--restore", "LB-0001", "1", "--store", tmp_path / "s.json")
    assert code == 2 and "no history" in err


def test_no_arguments_is_a_usage_error():
    with pytest.raises(SystemExit):
        main([])
