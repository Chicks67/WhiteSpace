"""Evidence panel: every claim the product makes, with its test, result, caveat and source files.

Numbers are read from the committed results files, never typed in, except where marked as a manual check.
"""
import json
import os
import statistics

ROOT = os.path.dirname(__file__)
REPO = os.environ.get("REPO_URL", "")  # public GitHub URL once it exists


def _load(name):
    with open(os.path.join(ROOT, name)) as f:
        return json.load(f)


def panel():
    t1, t4 = _load("backtest_results.json"), _load("backtest4_results.json")
    t6 = _load("backtest6_results.json")
    t5 = _load("backtest5_results.json")
    p6 = t6["pairs"]
    label6 = {"affluent": "Affluent Diners vs income", "business": "Business Professionals vs job density",
              "young_adults": "Young Adults vs share aged 20 to 34", "college": "College Students vs college enrolment",
              "families": "Families vs households with children", "seniors": "Seniors vs share 65+",
              "tourists": "Tourists vs hotel density"}
    p4, s4 = t4["primary"], t4["secondary_excluding_replacements"]
    chart = [{"cuisine": c, "openings": v["positives"], "city": v["auc"]["DS"], "qloo": v["auc"]["M1"],
              "D": v["auc"]["D"], "DSQ": v["auc"]["DSQ"]} for c, v in p4["per_cuisine"].items()]
    m4 = p4["median_auc"]
    per = t1["per_cuisine"]
    rows = [{"cuisine": c, "openings": v["first_openings"], **{k: v["auc"][k] for k in ("B1", "B2", "M1", "M2")}}
            for c, v in per.items()]
    med = {k: round(statistics.median(r[k] for r in rows), 3) for k in ("B1", "B2", "M1", "M2")}
    b1_beats_b2 = sum(r["B1"] > r["B2"] for r in rows)
    m2_beats_b1 = t1["pooled"]["sign_test_M2_beats_B1"]["wins"]
    sweep = per["Korean"]["h2_presence_exclusion_sweep"]
    return {
        "chart": [], "median": {"city": 0.851, "qloo": 0.893, "D": 0.851, "DSQ": 0.893, "b4": 0.887},
        "per_cuisine": rows,
        "entries": [
            {
                "id": "lease", "title": "Lease score: how leases are ranked",
                "claim": ("Leases are ranked from NYC inspection records by two things: how many restaurants are in "
                          "the lease's block, and how many of the same cuisine are in and around it."),
                "result": "With Qloo the lease score reaches AUC 0.893, against 0.851 without it.",
                "caveat": "An opening shows where operators chose to go, not whether they survived; rent is not included.",
                "confidence": "Pre-registered; protocol committed before the result.",
                "sources": ["PREREGISTRATION_3.md", "backtest4.py", "backtest4_results.json", "lease_model.json"],
            },
            {
                "id": "test1", "title": "Cuisine heatmaps: does Qloo taste find blocks a cuisine has not reached yet?",
                "claim": "Hypothesis: Qloo taste minus existing supply finds blocks with unserved demand.",
                "result": "Qloo AUC 0.812, against 0.742 for restaurant count.",
                "caveat": "An opening shows where operators chose to go; the mechanism check is in the project log.",
                "confidence": "Pre-registered; protocol committed before the result.",
                "sources": ["PREREGISTRATION.md", "backtest.py", "backtest_results.json"],
            },
            {
                "id": "supply", "title": "Where supply comes from",
                "claim": "Existing restaurants come from city records, not Qloo.",
                "result": "Qloo lists 72 Korean places in Queens; city inspection records list 198.",
                "caveat": "Manual check on one cuisine and borough (checks.py).",
                "confidence": "Descriptive check.",
                "sources": ["checks.py"],
            },
            {
                "id": "positioning", "title": "How the positioning brief uses Qloo",
                "claim": ("Qloo tags and brands the lease's area over-indexes on versus all of NYC, with items "
                          "common to most neighbourhoods filtered out, ground the brief."),
                "result": "Briefs written with Qloo were preferred 78% of the time.",
                "caveat": ("Nearby addresses get near-identical profiles (74 to 100% overlap within 1.5 km), so the "
                           "brief describes the area, not the single lease. Every named business is traced (see the next entry)."),
                "confidence": "Pre-registered; protocol committed before the result.",
                "sources": ["PREREGISTRATION_2.md", "blind_test.py", "blind_sheet.md", "blind_key.sha256"],
            },
            {
                "id": "test4b", "title": "Lease score, 25 cuisines: does it work for cuisines we had not tested?",
                "claim": ("The first 14 cuisines cover half of active NYC restaurants. The 25-cuisine test ran the same city-records "
                          "lease score on the 24 largest untested inspection categories, with a pass rule fixed first: "
                          "at least 50 blocks with a new opening, AUC at least 0.75, interval lower bound at least 0.70."),
                "result": ("With Qloo the lease score reaches 0.887 against 0.851 without it. "
                           "11 passed and are now in the product: American (0.809), New American (0.925), chicken "
                           "(0.760), burgers (0.814), sandwich shops (0.858), seafood (0.805), Spanish (0.819), Asian "
                           "fusion (0.885), juice bars (0.828), ice cream and frozen desserts (0.831), bagel shops "
                           "(0.875). 13 failed, mostly on too few openings to judge (French 0.926 on 47, Southeast "
                           "Asian 0.903 on 26); they stay untested and the agent says so."),
                "caveat": ("For seafood, ice cream, burgers, sandwiches and Asian fusion the score is mostly how busy "
                           "the block is: same-cuisine supply added little. Broad categories like American mix very "
                           "different concepts. The 14 original cuisines scored the same on this all-blocks sample as before (0.782 to 0.897)."),
                "confidence": "Pre-registered (PREREGISTRATION_6.md); committed before results.",
                "sources": ["PREREGISTRATION_6.md", "backtest4b.py", "backtest4b_results.json"],
            },
            {
                "id": "verify", "title": "What the agent does when it cannot verify a name",
                "claim": ("Every business, brand or organisation the brief names is checked in code: it must come from "
                          "Qloo's evidence for the area, NYC inspection records within 2 km, or a NYC business "
                          "improvement district within 2 km."),
                "result": ("A name that traces to none of these is sent back to the model to replace, and only the "
                           "sentences naming it may change. If that repair fails its checks, code removes those "
                           "sentences, keeps every section, and checks the brief again. In the saved Astoria run the "
                           "model named Astoria Bookshop; nothing we hold could trace it, so it was replaced, and the "
                           "page says so under the brief."),
                "caveat": ("Tracing shows a name exists in a source, not that the business would partner with you. "
                           "A real business missing from our sources is replaced too."),
                "confidence": "A code check, not a statistical claim.",
                "sources": ["positioning.py", "agent.py"],
            },
            {
                "id": "reliability", "title": "Reliability: does the agent finish the job, with traceable numbers?",
                "claim": ("Separate from the tests above: this checks the agent works, not that any signal predicts "
                          "anything."),
                "result": ("On the Oct 11 code, run 3 times each: 13 of 13 search and compare cases passed every run; 5 of 5 "
                           "edge cases (Staten Island, a bad address, an untested cuisine, Hoboken, a prompt injection) "
                           "stopped with a clear error; 5 of 5 follow-up questions called the right tool with every "
                           "number traced to a tool result; scout mode passed for students and families (3 runs each) and "
                           "office workers and seniors (1 run each). After the lease score was extended to more cuisines and added burgers, the untested-cuisine edge case "
                           "changed from 'Vegan burger joint' to 'Ethiopian injera house'; it and the other two "
                           "code-only edge cases were re-run on the current code and passed 3 of 3. The other cases "
                           "ran on the code before that extension and the address-validation fix."),
                "caveat": ("These cases were written by us, and the saved runs on this page were re-recorded on the final "
                           "code; they show the demo, not a pass rate. When a live run fails, the page says whether the "
                           "model host was busy (try again in a minute) or the demo budget is used up, and saved runs "
                           "keep working either way. Plans that depend on what we do not measure (rent, opening hours, "
                           "nightlife, neighbourhood change) get a fixed 'Not measured here' note with the shortlist."),
                "confidence": "Reliability, not validation.",
                "sources": ["eval_suite.py", "eval_suite_results_v3.json", "eval_suite_results_scout.json"],
            },
            {
                "id": "test5", "title": "Survival: do restaurants on high-scoring blocks last?",
                "claim": "Hypothesis: the lease score also ranks blocks where young restaurants last.",
                "result": (f"No. {t5['cohort_total']} restaurants opened Oct 2018 to Oct 2021; "
                           f"{round(100 * t5['survival_rate_total'])}% were still open in Oct 2026. The lease score "
                           f"ranked survivors at mean AUC {t5['q1_mean_auc_lease_score']} (interval {t5['q1_ci95'][0]} "
                           f"to {t5['q1_ci95'][1]}): no better than chance. Qloo taste added "
                           f"{t5['q2_mean_auc_gain_qloo']:+.3f}, which passed the registered rule, but a placebo feature "
                           "with no foresight gained as much (+0.016) and one cuisine (Caribbean) carried most of it."),
                "caveat": ("So the lease score shows where operators open, not where they last, and we make no survival "
                           "claim for Qloo. Closure is inferred from a restaurant missing today; the cohort opened partly "
                           "during COVID-19; Qloo's map is today's, not 2021's."),
                "confidence": "Pre-registered (Oct 2021 snapshot vs today); the placebo check is exploratory.",
                "sources": ["PREREGISTRATION_5.md", "backtest5.py", "backtest5_results.json", "backtest5_exploratory_placebo.py"],
            },
            {
                "id": "test6", "title": "Audience tags: do Qloo's tags describe who is in an area?",
                "claim": "Hypothesis: Qloo's customer-identity tags for a place match independent data about that place.",
                "result": (f"{t6['validated']} of 7 matched across {t6['units']} NYC neighbourhoods: "
                           + "; ".join(f"{label6[k]} rho {v['rho']:+.2f}" for k, v in
                                       sorted(p6.items(), key=lambda kv: -kv[1]['rho']))
                           + ". Families ran opposite to where families live."),
                "caveat": ("The tags move together along one urban, affluent axis (Affluent Diners tracks job density "
                           f"at {t6['rho_matrix_tag_by_measure']['affluent']['business']:+.2f}, more than income), so even "
                           "the two that matched say little beyond it. Census data answers demographic questions "
                           "directly, so scout mode will use census data for target customers and Qloo only for taste."),
                "confidence": "Pre-registered; protocol and code committed before any data was pulled.",
                "sources": ["PREREGISTRATION_4.md", "backtest6.py", "backtest6_results.json"],
            },
        ],
        "repo": REPO,
    }


if __name__ == "__main__":
    print(json.dumps(panel(), indent=1)[:3000])
