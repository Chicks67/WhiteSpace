"""Record two follow-up questions for each saved run, so the site can replay them with no API calls."""
import json
import os
import time

import followup

QUESTIONS = {
    "scout-students": ["Who could I partner with for cross-promotion near the top storefront?",
                       "Why is the top pick better than a storefront in Morningside Heights, where the student share is highest?"],
    "scout-families": ["How many pizzerias are within 400 m of the top storefront, and which opened recently?",
                       "Find vacant storefronts in Forest Hills and compare the best one with our top pick."],
    "korean-cafe-astoria": ["Who are the Korean competitors within 300 m of the top storefront?",
                            "Find vacant storefronts in Sunnyside and compare the best one with our top storefront."],
    "korean-cafe-queens": ["Why does 41-08 Bell Blvd rank last when Qloo taste puts it first?",
                           "Is Kung Fu Tea near the top lease in city records?"],
    "ramen-williamsburg": ["Who are the ramen and Japanese competitors within 400 m of the top storefront?",
                           "What does Qloo say about the audience around the top storefront?"],
    "caribbean-brooklyn-bronx": ["Find vacant storefronts in Flatbush and compare them with 600 Nostrand Ave.",
                                 "Does Qloo predict where a Caribbean restaurant should open?"],
}

import sys
only = sys.argv[1:]
for rid, qs in QUESTIONS.items():
    if only and rid not in only:
        continue
    path = f"golden/{rid}.json"
    if not os.path.exists(path):
        print(rid, "no saved run"); continue
    g = json.load(open(path))
    ctx = followup.compact_context([e for _, e in g["events"]])
    saved, history = [], []
    for q in qs:
        for attempt in range(3):  # Kie sometimes stalls before answering; a saved answer is worth a retry
            events, t0 = [], time.time()
            try:
                followup.ask(q, ctx, history, lambda e: events.append([round(time.time() - t0, 2), e]))
                break
            except Exception as e:
                print(rid, "| retry after:", str(e)[:80], flush=True)
        else:
            continue
        ans = next(e for _, e in events if e["type"] == "answer")
        history.append({"q": q, "a": ans["text"]})
        saved.append({"q": q, "events": events})
        print(rid, "|", q, "|", round(events[-1][0], 1), "s |", [e["name"] for _, e in events if e["type"] == "tool" and e["status"] == "done"],
              "| unchecked:", ans["unchecked_numbers"], flush=True)
    if len(saved) < len(qs):  # never replace a saved set with a partial one
        print(rid, "| not saved: only", len(saved), "of", len(qs), "answered", flush=True)
        continue
    g["followups"] = saved
    json.dump(g, open(path, "w"), indent=1)
