"""Store: an in-memory archive that can be saved to and loaded from JSON."""
from helpers import record

from safesync import Store


def test_save_version_numbers_start_at_one_and_copy_the_record():
    store = Store(records={"LB-0001": record("LB-0001")})

    assert store.save_version("LB-0001") == 1
    store.records["LB-0001"]["branch"] = "north"
    assert store.save_version("LB-0001") == 2

    assert store.versions["LB-0001"][0]["record"]["branch"] == "central"
    assert store.versions["LB-0001"][1]["record"]["branch"] == "north"


def test_json_round_trip(tmp_path):
    store = Store(records={"LB-0001": record("LB-0001")})
    store.save_version("LB-0001")
    path = tmp_path / "store.json"

    store.save(path)
    loaded = Store.load(path)

    assert loaded.to_dict() == store.to_dict()


def test_loading_a_missing_file_gives_an_empty_store(tmp_path):
    loaded = Store.load(tmp_path / "nope.json")

    assert loaded.records == {} and loaded.versions == {}
