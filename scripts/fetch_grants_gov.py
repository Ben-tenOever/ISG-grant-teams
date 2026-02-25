#!/usr/bin/env python3
import argparse, json, time
import urllib.request
from pathlib import Path

SEARCH_URL = "https://api.grants.gov/v1/api/search2"
FETCH_URL  = "https://api.grants.gov/v1/api/fetchOpportunity"

def post_json(url: str, payload: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", default="")
    ap.add_argument("--agencies", default="")
    ap.add_argument("--status", default="posted|forecasted")
    ap.add_argument("--rows", type=int, default=100)
    ap.add_argument("--max", type=int, default=300)
    ap.add_argument("--out", default="data/opportunities.json")
    ap.add_argument("--sleep", type=float, default=0.25)
    args = ap.parse_args()

    hits = []
    start = 0
    while len(hits) < args.max:
        payload = {
            "rows": args.rows,
            "startRecordNum": start,
            "keyword": args.keyword,
            "agencies": args.agencies,
            "oppStatuses": args.status,
        }
        res = post_json(SEARCH_URL, payload)
        data = res.get("data", {})
        opp_hits = data.get("oppHits", []) or []
        if not opp_hits:
            break
        hits.extend(opp_hits)
        start += args.rows
        hit_count = data.get("hitCount") or 0
        if start >= hit_count:
            break

    hits = hits[:args.max]

    out = []
    for h in hits:
        opp_id = int(h["id"])
        det = post_json(FETCH_URL, {"opportunityId": opp_id})
        d = det.get("data", {})
        syn = d.get("synopsis", {}) or {}
        out.append({
            "id": d.get("id", opp_id),
            "number": d.get("opportunityNumber") or h.get("number"),
            "title": d.get("opportunityTitle") or h.get("title"),
            "agencyCode": d.get("owningAgencyCode") or h.get("agencyCode"),
            "agencyName": syn.get("agencyName") or h.get("agencyName"),
            "oppStatus": h.get("oppStatus"),
            "postingDate": syn.get("postingDate") or h.get("openDate"),
            "closeDate": h.get("closeDate"),
            "synopsis": (syn.get("synopsisDesc") or "").strip(),
            "url": f"https://www.grants.gov/search-results-detail/{opp_id}",
        })
        time.sleep(args.sleep)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(out)} opportunities to {args.out}")

if __name__ == "__main__":
    main()
