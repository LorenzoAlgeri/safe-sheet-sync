"""Sync a CSV sheet into a local JSON store.

    python sync.py --dry-run example/members.csv    show the plan, write nothing
    python sync.py example/members.csv              apply the same plan
    python sync.py --history LB-0002                list saved versions of a record
    python sync.py --restore LB-0002 1              put version 1 back
"""
import argparse
import csv
import sys
from pathlib import Path

from safesync import Store, apply, format_plan, plan, restore


def read_sheet(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return [
            {(k or "").strip(): v for k, v in row.items()} for row in reader
        ]


def build_parser():
    parser = argparse.ArgumentParser(prog="sync.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sheet", nargs="?", help="CSV file to sync from")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    parser.add_argument("--store", default="store.json", help="JSON store (default: store.json)")
    parser.add_argument("--history", metavar="ID", help="list the saved versions of a record")
    parser.add_argument("--restore", nargs=2, metavar=("ID", "VERSION"),
                        help="put a saved version back")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not (args.sheet or args.history or args.restore):
        parser.error("give a sheet to sync, or --history ID, or --restore ID VERSION")

    store = Store.load(args.store)

    if args.history:
        versions = store.versions.get(args.history)
        if not versions:
            print(f"no history for record {args.history}", file=sys.stderr)
            return 2
        for item in versions:
            r = item["record"]
            print(f"version {item['version']}: phone={r.get('phone') or '(empty)'}, "
                  f"branch={r.get('branch') or '(empty)'}, tags={', '.join(r.get('tags', [])) or '(none)'}")
        return 0

    if args.restore:
        record_id, number = args.restore
        try:
            restore(store, record_id, int(number))
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 2
        store.save(args.store)
        print(f"Restored {record_id} to version {number}. "
              f"The state it replaced is saved as the latest version.")
        return 0

    if not Path(args.sheet).exists():
        print(f"sheet not found: {args.sheet}", file=sys.stderr)
        return 2

    the_plan = plan(read_sheet(args.sheet), store)
    print(format_plan(the_plan))
    print("\n== result ==")

    if args.dry_run:
        print("Dry run: nothing was written.")
        return 0

    result = apply(the_plan, store)
    if not result["created"] and not result["updated"]:
        print("Nothing to change.")
    else:
        store.save(args.store)
        print(f"Applied: {len(result['created'])} created, {len(result['updated'])} updated, "
              f"{len(result['skipped'])} skipped.")
    for item in result["skipped"]:
        field = f" {item['field']}" if item["field"] else ""
        print(f"  skipped {item['key']}{field}: {item['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
