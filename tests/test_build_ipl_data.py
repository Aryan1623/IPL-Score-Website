import json
import tempfile
import unittest
from pathlib import Path

from scripts import build_ipl_data


class BuildIplDataTests(unittest.TestCase):
    def test_team_short_name_uses_known_mapping(self):
        self.assertEqual(build_ipl_data.team_short_name("Mumbai Indians"), "MI")
        self.assertEqual(build_ipl_data.team_short_name("Unknown Team"), "UNK")

    def test_build_result_text_handles_wins_ties_and_no_result(self):
        self.assertEqual(
            build_ipl_data.build_result_text(
                {"winner": "Chennai Super Kings", "by": {"runs": 12}}
            ),
            "Chennai Super Kings won by 12 runs",
        )
        self.assertEqual(
            build_ipl_data.build_result_text(
                {"winner": "Mumbai Indians", "by": {"wickets": 6}}
            ),
            "Mumbai Indians won by 6 wickets",
        )
        self.assertEqual(build_ipl_data.build_result_text({"result": "tie"}), "Match tied")
        self.assertEqual(
            build_ipl_data.build_result_text({"result": "no result"}),
            "No result",
        )

    def test_calculate_innings_totals_counts_only_legal_deliveries_for_overs(self):
        innings = {
            "team": "Mumbai Indians",
            "overs": [
                {
                    "deliveries": [
                        {"runs": {"total": 1}, "extras": {}},
                        {"runs": {"total": 2}, "extras": {"wides": 1}},
                        {"runs": {"total": 4}, "extras": {}},
                        {"runs": {"total": 0}, "extras": {}, "wickets": [{"kind": "bowled"}]},
                        {"runs": {"total": 1}, "extras": {"noballs": 1}},
                        {"runs": {"total": 3}, "extras": {}},
                        {"runs": {"total": 1}, "extras": {}},
                    ]
                }
            ],
        }

        totals = build_ipl_data.calculate_innings_totals(innings)

        self.assertEqual(totals["runs"], 12)
        self.assertEqual(totals["wickets"], 1)
        self.assertEqual(totals["overs"], "0.5")
        self.assertEqual(totals["shortName"], "MI")

    def test_build_match_summary_reads_expected_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            match_file = temp_path / "sample_match.json"
            sample_match = {
                "info": {
                    "dates": ["2017-04-05"],
                    "season": "2017",
                    "event": {"match_number": 1, "name": "Indian Premier League"},
                    "venue": "Rajiv Gandhi International Stadium",
                    "city": "Hyderabad",
                    "teams": ["Sunrisers Hyderabad", "Royal Challengers Bangalore"],
                    "outcome": {"winner": "Sunrisers Hyderabad", "by": {"runs": 35}},
                    "player_of_match": ["Yuvraj Singh"],
                    "toss": {"winner": "Royal Challengers Bangalore", "decision": "field"},
                },
                "innings": [
                    {
                        "team": "Sunrisers Hyderabad",
                        "overs": [
                            {
                                "deliveries": [
                                    {"runs": {"total": 1}, "extras": {}},
                                    {"runs": {"total": 4}, "extras": {}},
                                    {"runs": {"total": 0}, "extras": {}, "wickets": [{"kind": "caught"}]},
                                ]
                            }
                        ],
                    },
                    {
                        "team": "Royal Challengers Bangalore",
                        "overs": [
                            {
                                "deliveries": [
                                    {"runs": {"total": 2}, "extras": {}},
                                    {"runs": {"total": 1}, "extras": {}},
                                ]
                            }
                        ],
                    },
                ],
            }
            match_file.write_text(json.dumps(sample_match), encoding="utf-8")

            summary = build_ipl_data.build_match_summary(match_file)

        self.assertEqual(summary["id"], "sample_match")
        self.assertEqual(summary["season"], "2017")
        self.assertEqual(summary["teams"][0]["shortName"], "SRH")
        self.assertEqual(summary["winner"], "Sunrisers Hyderabad")
        self.assertIn("won by 35 runs", summary["resultText"])
        self.assertEqual(len(summary["innings"]), 2)

    def test_main_writes_payload_to_output_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "ipl_json"
            source_dir.mkdir(parents=True, exist_ok=True)

            sample_match = {
                "info": {
                    "dates": ["2024-01-01"],
                    "season": "2024",
                    "event": {"match_number": 1, "name": "Indian Premier League"},
                    "venue": "Test Stadium",
                    "city": "Test City",
                    "teams": ["Mumbai Indians", "Chennai Super Kings"],
                    "outcome": {"winner": "Mumbai Indians", "by": {"runs": 10}},
                    "player_of_match": ["Sample Player"],
                    "toss": {"winner": "Mumbai Indians", "decision": "bat"},
                },
                "innings": [
                    {
                        "team": "Mumbai Indians",
                        "overs": [
                            {
                                "deliveries": [
                                    {"runs": {"total": 1}, "extras": {}},
                                    {"runs": {"total": 4}, "extras": {}},
                                ]
                            }
                        ],
                    }
                ],
            }

            match_file = source_dir / "sample.json"
            match_file.write_text(json.dumps(sample_match), encoding="utf-8")

            original_raw_dir = build_ipl_data.RAW_DATA_DIR
            original_zip_file = build_ipl_data.RAW_ZIP_FILE
            original_output_file = build_ipl_data.OUTPUT_FILE

            build_ipl_data.RAW_DATA_DIR = source_dir
            build_ipl_data.RAW_ZIP_FILE = temp_path / "ipl_json.zip"
            build_ipl_data.OUTPUT_FILE = temp_path / "matches.json"
            try:
                build_ipl_data.main()
            finally:
                build_ipl_data.RAW_DATA_DIR = original_raw_dir
                build_ipl_data.RAW_ZIP_FILE = original_zip_file
                build_ipl_data.OUTPUT_FILE = original_output_file

            payload = json.loads((temp_path / "matches.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["matchCount"], 1)
            self.assertEqual(payload["latestMatchDate"], "2024-01-01")
            self.assertEqual(payload["matches"][0]["winner"], "Mumbai Indians")


if __name__ == "__main__":
    unittest.main()
