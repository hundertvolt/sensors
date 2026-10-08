"""Builds the owner review page from topics.json and decisions.json into review.html."""

import json
import pathlib

HERE = pathlib.Path(__file__).parent


def merge_routine(data: dict, extra: dict) -> None:
    """Turns each routine decision into a read-only settlement or a member of one open question."""
    merge = json.loads((HERE / "routine_merge.json").read_text())
    settled, questions = {}, list(extra.get("open_extra", []))
    for share in "ABCD":
        part = json.loads((HERE / f"routine_{share}.json").read_text())
        for s in part["settled"]:
            settled[s["id"]] = s
        questions += part["for_owner"]
    for q in merge["to_owner"]:
        for m in q["members"]:
            settled.pop(m)
        questions.append(q)
    routine = [d for d in data["decisions"] if d["weight"] == "routine"]
    members = [m for q in questions for m in q["members"]]
    seen = sorted(list(settled) + members)
    want = sorted(d["id"] for d in routine)
    if seen != want:
        raise SystemExit(f"routine accounting: missing {sorted(set(want) - set(seen))}, extra or doubled {sorted(i for i in set(seen) if seen.count(i) != 1 or i not in want)}")
    titles = {d["id"]: d["title"] for d in routine}
    for d in routine:
        if d["id"] in settled:
            s = settled[d["id"]]
            d.update(weight="settled", step=s["step"], settled_why=s["why"], outcome=merge["outcome"].get(d["id"], ""))
            d["refs"] = list(d.get("refs", [])) + [c.strip() for c in s["cite"].split(";") if c.strip()]
    data["decisions"] = [d for d in data["decisions"] if d["weight"] != "routine"]
    for q in questions:
        q = dict(q, weight="open", member_titles=[titles[m] for m in q["members"]], answered=extra.get("answered_in_chat", {}).get(q["id"]))
        data["decisions"].insert(0, q)
    print(f"routine: {len(settled)} settled, {len(questions)} open questions covering {len(members)} items")


def main() -> None:
    topics = json.loads((HERE / "topics.json").read_text())
    decisions = json.loads((HERE / "decisions.json").read_text())
    extra = json.loads((HERE / "page_extra.json").read_text()) if (HERE / "page_extra.json").exists() else {}
    data = {
        "overview": topics["overview"],
        "topics": topics["topics"],
        "topicTitles": {t["id"]: t["title"] for t in topics["topics"]},
        "owner_steps": decisions.get("owner_steps", []),
        "hardware_sessions": decisions.get("hardware_sessions", []),
        "decisions": decisions.get("decisions", []),
        "parked": decisions.get("parked", []),
        "go_summary": extra.get("go_summary", ""),
        "replies": extra.get("replies", {}),
    }
    merge_routine(data, extra)
    ids = [d["id"] for d in data["decisions"]]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise SystemExit(f"duplicate decision ids: {sorted(dupes)}")
    unknown = {d["topic"] for d in data["decisions"]} - set(data["topicTitles"])
    if unknown:
        raise SystemExit(f"decisions name unknown topics: {sorted(unknown)}")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = (HERE / "page_template.html").read_text().replace("__REVIEW_DATA__", payload)
    (HERE / "review.html").write_text(page)
    print(f"review.html: {len(data['topics'])} topics, {len(ids)} decisions, {len(page) // 1024} KiB")


if __name__ == "__main__":
    main()
