import unittest

from scripts.jund_cleansing_wildfire_measurement import correlate_measurement, names, parse_card_refs, URZA


def ordinary(targets):
    lines = ["Turn: Turn 3 (Ai(1)-Jund Wildfire)", "Phase: Ai(1)-Jund Wildfire's Main phase, precombat"]
    for t in targets:
        lines.append(f"Add To Stack: Ai(1)-Jund Wildfire cast Cleansing Wildfire targeting [{t}]")
    return lines


class CleansingWildfireCorrelationTests(unittest.TestCase):
    def test_multiple_ai_probes_before_one_cast(self):
        text = "\n".join([
            "CWMEASURE kind=probe inv=1 sa=101 host=56 player=Jund turn=3 phase=MAIN candidates=Cave_of_Temptation#61 own=- high=- selected=- reason=stock-fallback targets=- evaluation=canPlay",
            "CWMEASURE kind=probe inv=2 sa=101 host=56 player=Jund turn=3 phase=MAIN candidates=Slagwoods_Bridge#26,Cave_of_Temptation#61 own=Slagwoods_Bridge#26 high=- selected=Slagwoods_Bridge#26 reason=self-indestructible targets=- evaluation=canPlay",
            "CWMEASURE kind=postselect inv=2 sa=101 host=56 player=Jund turn=3 phase=MAIN targets=Slagwoods_Bridge#26 evaluation=canPlay",
            "CWMEASURE kind=commit sa=101 host=56 player=Jund turn=3 phase=MAIN targets=Slagwoods_Bridge#26 committed=true",
            *ordinary(["Slagwoods Bridge (26)"]),
        ])
        r = correlate_measurement(text)
        self.assertEqual(r["correlations"][0]["status"], "correlated")
        self.assertEqual(r["correlations"][0]["probe"]["inv"], "2")
        self.assertEqual(r["correlations"][0]["probe_count_same_identity"], 2)
        self.assertEqual(len(r["uncommitted_probes"]), 1)

    def test_two_wildfires_in_one_game(self):
        text = "\n".join([
            "CWMEASURE kind=probe inv=1 sa=101 host=56 player=Jund turn=3 phase=MAIN candidates=Cave#61 own=- high=- selected=- reason=stock-fallback targets=- evaluation=canPlay",
            "CWMEASURE kind=commit sa=101 host=56 player=Jund turn=3 phase=MAIN targets=Cave#61 committed=true",
            "CWMEASURE kind=probe inv=2 sa=202 host=57 player=Jund turn=5 phase=MAIN candidates=Slagwoods_Bridge#26 own=Slagwoods_Bridge#26 high=- selected=Slagwoods_Bridge#26 reason=self-indestructible targets=- evaluation=canPlay",
            "CWMEASURE kind=postselect inv=2 sa=202 host=57 player=Jund turn=5 phase=MAIN targets=Slagwoods_Bridge#26 evaluation=canPlay",
            "CWMEASURE kind=commit sa=202 host=57 player=Jund turn=5 phase=MAIN targets=Slagwoods_Bridge#26 committed=true",
            *ordinary(["Cave (61)", "Slagwoods Bridge (26)"]),
        ])
        r = correlate_measurement(text)
        self.assertEqual([c["probe"]["reason"] for c in r["correlations"]], ["stock-fallback", "self-indestructible"])
        self.assertTrue(r["commit_count_matches_ordinary"])

    def test_buffered_ordinary_output_does_not_control_correlation(self):
        text = "\n".join([
            "CWMEASURE kind=probe inv=7 sa=303 host=58 player=Jund turn=7 phase=MAIN candidates=Slagwoods_Bridge#26 own=Slagwoods_Bridge#26 high=- selected=Slagwoods_Bridge#26 reason=self-indestructible targets=- evaluation=canPlay",
            "CWMEASURE kind=postselect inv=7 sa=303 host=58 player=Jund turn=7 phase=MAIN targets=Slagwoods_Bridge#26 evaluation=canPlay",
            "CWMEASURE kind=commit sa=303 host=58 player=Jund turn=7 phase=MAIN targets=Slagwoods_Bridge#26 committed=true",
            "Mulligan: buffered ordinary output begins here",
            *ordinary(["Slagwoods Bridge (26)"]),
        ])
        r = correlate_measurement(text)
        self.assertEqual(r["correlations"][0]["commit"]["sa"], "303")
        self.assertEqual(r["correlations"][0]["ordinary"]["target"]["id"], "26")

    def test_stock_fallback_followed_by_later_self_bridge(self):
        text = "\n".join([
            "CWMEASURE kind=probe inv=1 sa=101 host=56 player=Jund turn=3 phase=MAIN candidates=Ash_Barrens#88 own=- high=- selected=- reason=stock-fallback targets=- evaluation=canPlay",
            "CWMEASURE kind=commit sa=101 host=56 player=Jund turn=3 phase=MAIN targets=Ash_Barrens#88 committed=true",
            "CWMEASURE kind=probe inv=2 sa=202 host=57 player=Jund turn=9 phase=MAIN candidates=Slagwoods_Bridge#26,Ash_Barrens#88 own=Slagwoods_Bridge#26 high=- selected=Slagwoods_Bridge#26 reason=self-indestructible targets=- evaluation=canPlay",
            "CWMEASURE kind=postselect inv=2 sa=202 host=57 player=Jund turn=9 phase=MAIN targets=Slagwoods_Bridge#26 evaluation=canPlay",
            "CWMEASURE kind=commit sa=202 host=57 player=Jund turn=9 phase=MAIN targets=Slagwoods_Bridge#26 committed=true",
            *ordinary(["Ash Barrens (88)", "Slagwoods Bridge (26)"]),
        ])
        r = correlate_measurement(text)
        self.assertEqual([c["ordinary"]["target"]["id"] for c in r["correlations"]], ["88", "26"])

    def test_visible_tron_followed_by_self_bridge(self):
        text = "\n".join([
            "CWMEASURE kind=probe inv=1 sa=101 host=56 player=Jund turn=9 phase=MAIN candidates=Mine#94,Power_Plant#88,Bridge#26 own=Bridge#26 high=Urza's_Mine#94,Urza's_Power_Plant#88 selected=Urza's_Mine#94 reason=visible-tron targets=- evaluation=canPlay",
            "CWMEASURE kind=postselect inv=1 sa=101 host=56 player=Jund turn=9 phase=MAIN targets=Urza's_Mine#94 evaluation=canPlay",
            "CWMEASURE kind=commit sa=101 host=56 player=Jund turn=9 phase=MAIN targets=Urza's_Mine#94 committed=true",
            "CWMEASURE kind=probe inv=2 sa=202 host=57 player=Jund turn=9 phase=MAIN candidates=Power_Plant#88,Power_Plant#87,Bridge#26 own=Bridge#26 high=Urza's_Power_Plant#88,Urza's_Power_Plant#87 selected=Bridge#26 reason=self-indestructible targets=- evaluation=canPlay",
            "CWMEASURE kind=postselect inv=2 sa=202 host=57 player=Jund turn=9 phase=MAIN targets=Bridge#26 evaluation=canPlay",
            "CWMEASURE kind=commit sa=202 host=57 player=Jund turn=9 phase=MAIN targets=Bridge#26 committed=true",
            *ordinary(["Urza's Mine (94)", "Bridge (26)"]),
        ])
        r = correlate_measurement(text)
        self.assertEqual([c["probe"]["reason"] for c in r["correlations"]], ["visible-tron", "self-indestructible"])

    def test_duplicate_power_plants_are_one_distinct_urza_type(self):
        refs = parse_card_refs("Urza's_Power_Plant#88,Urza's_Power_Plant#87")
        self.assertEqual(len(names(refs) & URZA), 1)

    def test_missing_identity_is_uncorrelated_not_false_mismatch(self):
        text = "\n".join([
            "CWMEASURE kind=probe inv=1 sa=111 host=56 player=Jund turn=3 phase=MAIN candidates=Bridge#26 own=Bridge#26 high=- selected=Bridge#26 reason=self-indestructible targets=- evaluation=canPlay",
            "CWMEASURE kind=commit sa=222 host=56 player=Jund turn=3 phase=MAIN targets=Bridge#26 committed=true",
            *ordinary(["Bridge (26)"]),
        ])
        r = correlate_measurement(text)
        self.assertEqual(r["correlations"][0]["status"], "uncorrelated")
        self.assertNotIn("selected_target_disagrees_with_commit", r["correlations"][0]["issues"])


if __name__ == "__main__":
    unittest.main()
