"""Builds the owner review page from topics.json and decisions.json into review.html."""

import json
import pathlib

HERE = pathlib.Path(__file__).parent


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
    }
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
