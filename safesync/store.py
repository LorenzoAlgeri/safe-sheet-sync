"""An in-memory archive of records, each with a history of saved versions."""
import copy
import json
import os
from pathlib import Path


class Store:
    """records: key -> record. versions: key -> list of {"version", "record"}.

    Version n of a record is the state it had before its n-th change.
    """

    def __init__(self, records=None, versions=None):
        self.records = records if records is not None else {}
        self.versions = versions if versions is not None else {}

    def save_version(self, key):
        """Copy the current state of a record into its history. Returns the number."""
        history = self.versions.setdefault(key, [])
        number = len(history) + 1
        history.append({"version": number, "record": copy.deepcopy(self.records[key])})
        return number

    def to_dict(self):
        return {
            "records": copy.deepcopy(self.records),
            "versions": copy.deepcopy(self.versions),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(records=data.get("records", {}), versions=data.get("versions", {}))

    @classmethod
    def load(cls, path):
        path = Path(path)
        if not path.exists():
            return cls()
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, path):
        path = Path(path)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(tmp, path)
