"""A-C3 Part S helper: for a fan-out action, which files under given scopes carry it (From names it, Site/heading names the file)."""
import sys
sys.path.insert(0, "audit/sweeps")
import ac3_site_trace as t

def carriers(aid):
    ch, _ = t.parse_m()
    out = {}
    for c in ch:
        if aid in set(t.ids_in(c["slots"].get("From", ""))):
            ex = {t.canon(f) for f, _ in t.extract(c["slots"].get("Site", ""), context=c["sec_files"][0] if c["sec_files"] else None)}
            for f in ex | {t.canon(f) for f in c["sec_files"]}:
                out.setdefault(f, []).append(c["id"])
    return out

if __name__ == "__main__":
    aid = sys.argv[1]
    car = carriers(aid)
    for f in sys.argv[2:]:
        print(f, car.get(t.canon(f), "-- NO CARRIER"))
