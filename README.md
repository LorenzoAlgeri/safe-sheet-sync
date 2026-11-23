[Italiano](README.it.md)

# safe-sheet-sync

A Python library that syncs a spreadsheet into a record store without destroying anything. It has a dry run, an update that never erases data, and a restore from saved versions. Standard library only, plus pytest for the tests.

Author: Lorenzo Algeri

## The day six cards were overwritten

I built a web app for digital business cards: a personal page for each employee of a company group, opened by tapping an NFC tag or scanning a QR code. The staff list lived in a spreadsheet, so I wrote scripts to load it into the app.

The first import overwrote existing records. I had left a line in an inspection command that ran the script instead of just loading it. Six cards that already existed lost the fields the sheet doesn't have. I got everything back from the version history the database kept for every change, so no data was lost.

This repo rewrites the part that decides what changes, on an invented example: the members of a neighbourhood library. The original code is not here. Three rules came out of that day.

1. A dry run and a real write use the same plan. `plan()` works out what would be created, updated or left alone, and writes nothing. `apply()` takes that plan and does only what it says. There is no second code path that could disagree with the printed output.
2. A sync never erases. A blank cell in the sheet doesn't clear a filled field. Fields the sheet doesn't own (`notes` and `loan_limit` in the example) are never touched after creation. Tags added by hand stay. Records that disappear from the sheet are reported, never deleted.
3. Every record is versioned before it is touched. `restore()` puts a version back, and it saves the state it replaces first, so you can undo a restore too.

## Try it in 5 minutes

You need Python 3.9 or newer.

```
pip install pytest
python -m pytest
python sync.py --dry-run example/members.csv
python sync.py example/members.csv
python sync.py example/members.csv
```

The first sync command shows 12 members to create and writes nothing. The second applies them to `store.json`. The third finds nothing to do.

Now the sheet with the interesting cases. Open `store.json` and change `notes` of `LB-0004` to any text. Then:

```
python sync.py --dry-run example/members_march.csv
```

You get this plan:

```
PLAN: 1 to create, 4 to update, 5 unchanged, 2 not in sheet, 4 rows skipped

CREATE (1)
  + LB-0013  Mona Newmember | north | adult

UPDATE (4)
  ~ LB-0002  Ben Sample
      phone: 000 000 0002 -> 000 000 0102
  ~ LB-0003  Cora Example
      phone: (empty) -> 000 000 0003
  ~ LB-0005  Eve Fictional
      branch: north -> central
  ~ LB-0007  Gus Mock
      tags: history -> history, poetry

UNCHANGED (5)
  LB-0001, LB-0004, LB-0006, LB-0009, LB-0011

NOT IN SHEET, reported only, nothing is deleted (2)
  ? LB-0008
  ? LB-0012

SKIPPED ROWS (4)
  ! data row 8: no card number
  ! data row 10 LB-0009: duplicate of data row 9, same values
  ! data row 11 LB-0010: conflicting duplicate rows, record left alone
  ! data row 12 LB-0010: conflicting duplicate rows, record left alone
```

What to look at:

- `LB-0001` has the same phone written in another format, so it isn't a change.
- `LB-0004` has a blank phone in the sheet. The stored phone stays, and so does the note you typed.
- `LB-0010` appears twice with different values. The sync doesn't guess: it leaves the record alone and says why.
- `LB-0008` is "not in sheet" only because its row has no card number. Whoever reads the plan can see that.

Run the same command without `--dry-run` to apply it. The printed plan is identical. Then:

```
python sync.py --history LB-0002
python sync.py --restore LB-0002 1
```

## What each file does

```
sync.py              command line
safesync/core.py     plan, apply, restore
safesync/store.py    in-memory store with versions, JSON load and save
safesync/report.py   turns a plan into text
example/             two invented sheets
tests/               43 tests
```

## Left out on purpose

The app I built has a database, a login, an editor, public pages and the logic that decides which fields a visitor sees. None of that is here. There is no network access, and the data is invented: every name in the example is made up. There are no credentials in the repo either.

I left those parts out for two reasons. They would show how the live system is built, and that isn't mine to publish. They are also not the interesting part. The decision logic is what failed, so that's what I rewrote, with a plain dictionary in place of a database.

A test (`tests/test_no_leaks.py`) checks that the repo contains no addresses, paths, keys or private words. It can miss things, so I still read the diff before publishing.

## The original app, counted

Counted on the original repository on 20 November 2026:

- 48 commits across all branches, from 24 April to 21 October 2026. 31 of them have Claude as co-author.
- The first import overwrote 6 of 6 existing cards, and all 6 came back from the version history.
- 62 test cases in 6 files, counted with grep. I didn't run them. None of them covered the import and sync scripts. This repo does, with 43 tests.
- A remediation plan in 9 phases, estimated at 27 to 30 hours and ordered by risk. It came from a code review of 7 areas. At the last check only phase 0 and part of phase 1 were done.

## Review first, then tests

Before fixing anything I had Claude review the whole codebase and then plan the fixes in phases. The plan asked for the work to be split across subagents and for a check before any task was called finished. I wrote up the import incident with its cause, its recovery and its fix, and the fix became the rule above: every script that writes starts as a dry run. Two things changed in how I work. Every script that writes data has a dry run, and I read it before the real run. Before I touch real data, I save a copy or a version I can go back to.

I wrote this extract the same way. The tests came first, as files, and I ran them red before any of the code existed. Then Claude Code wrote the code until they passed. I decided the rules and the checks.

## Limits

- Records are matched on one column. There is no fuzzy matching.
- Tags are only added. A tag removed from the sheet stays in the store.
- The check for stale plans works per field. It isn't a lock, so two syncs at the same moment can still race.
- The store is a JSON file, loaded fully into memory. It's there to model the logic, nothing more.
- The phone comparison ignores a leading `39` country code and non-digits. Other formats are compared as plain digits.
- The rules come from the original, but I didn't run this code and the original side by side.

## License

MIT. See `LICENSE`.
