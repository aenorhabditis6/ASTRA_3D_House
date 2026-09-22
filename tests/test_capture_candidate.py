"""The proposal must clear real preflight without weakening frozen source facts."""
import copy
import hashlib
import json
import unittest
from pathlib import Path

from astra_house.capture import CapturePlan
from astra_house.capture_geometry import analyze_capture_plan, quantize_m
from astra_house.io import load_room
from astra_house.measurements import MeasurementSet
from scripts.build_capture_candidate import anchor_points, make_candidate

PROJECT = Path("projects/dorm-right-bedroom")


class CandidateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((PROJECT / "capture-plan.json").read_text())
        cls.room = load_room(PROJECT / "room.json")
        cls.data = make_candidate(cls.source, cls.room)
        cls.plan = CapturePlan.from_dict(cls.data)

    def test_candidate_is_separate_deterministic_and_preserves_optics(self):
        before = copy.deepcopy(self.source)
        self.assertEqual(make_candidate(self.source, self.room), self.data)
        self.assertEqual(self.source, before)
        self.assertEqual(self.data["device_profile"], self.source["device_profile"])
        self.assertEqual(self.data["stations"], self.source["stations"])
        self.assertEqual(self.data["wall_review"], self.source["wall_review"])
        self.assertNotEqual(self.data["capture_id"], self.source["capture_id"])
        self.assertNotIn("coverage_review", self.data)
        self.assertEqual([len(m.shots) for m in self.plan.modes], [32,64])

    def test_candidate_clears_real_geometry_gate_and_anchor_baselines(self):
        measurements = MeasurementSet.from_dict(json.loads((PROJECT / "measurements.json").read_text()))
        self.plan.validate(self.room, measurements)
        digest = hashlib.sha256(json.dumps(self.room.to_dict(), sort_keys=True).encode()).hexdigest()
        for mode in analyze_capture_plan(self.plan, self.room, digest):
            self.assertEqual([issue for issue in mode.issues if issue.severity == "error"], [])
            self.assertEqual(len(mode.anchor_station_baselines_m), 7)
            self.assertTrue(all(count >= 2 and baseline >= .5 for _,count,baseline in mode.anchor_station_baselines_m))
            self.assertTrue(all(count >= 2 and baseline >= .5 for _,count,baseline in mode.wall_station_baselines_m))

    def test_full_measured_extents_are_kept_from_two_distinct_stations(self):
        for mode in self.plan.modes:
            for anchor in self.data["scale_anchors"]:
                target = anchor["target_id"]
                expected = {tuple(quantize_m(v) for v in p) for p in anchor_points(self.room, target)}
                stations = set()
                for group in mode.groups:
                    for shot in group.shots:
                        actual = {(p.x,p.y,p.z) for p in shot.framing_points_m}
                        if target in shot.target_ids and expected <= actual:
                            stations.add(group.station_id)
                self.assertGreaterEqual(len(stations), 2, f"{mode.id}/{target} lost measured extent")


if __name__ == "__main__":
    unittest.main()
