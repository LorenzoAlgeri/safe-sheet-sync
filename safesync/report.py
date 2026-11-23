"""Turn a plan into the text that --dry-run prints."""


def show(value):
    if isinstance(value, list):
        value = ", ".join(value)
    return "(empty)" if value in (None, "") else str(value)


def format_plan(the_plan):
    p = the_plan
    lines = [
        f"PLAN: {len(p['creates'])} to create, {len(p['updates'])} to update, "
        f"{len(p['unchanged'])} unchanged, {len(p['absent'])} not in sheet, "
        f"{len(p['skipped'])} rows skipped",
        "",
        f"CREATE ({len(p['creates'])})",
    ]
    for item in p["creates"]:
        r = item["record"]
        name = f"{r['first_name']} {r['last_name']}".strip() or "(no name)"
        lines.append(f"  + {item['key']}  {name} | {show(r['branch'])} | {show(r['membership'])}")

    lines += ["", f"UPDATE ({len(p['updates'])})"]
    for item in p["updates"]:
        lines.append(f"  ~ {item['key']}  {item['label']}".rstrip())
        for field, change in item["changes"].items():
            lines.append(f"      {field}: {show(change['from'])} -> {show(change['to'])}")

    lines += ["", f"UNCHANGED ({len(p['unchanged'])})"]
    if p["unchanged"]:
        lines.append("  " + ", ".join(p["unchanged"]))

    lines += ["", f"NOT IN SHEET, reported only, nothing is deleted ({len(p['absent'])})"]
    lines += [f"  ? {key}" for key in p["absent"]]

    lines += ["", f"SKIPPED ROWS ({len(p['skipped'])})"]
    for s in p["skipped"]:
        who = f" {s['key']}" if s["key"] else ""
        lines.append(f"  ! data row {s['row']}{who}: {s['reason']}")
    return "\n".join(lines)
