from datetime import date
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from wmdr2_projection import SourceRecord, choose_latest_by_wsi, extract_wsi, is_current, project_record


class ProjectionTests(unittest.TestCase):
    def fixture(self, name: str = "20250504_0-20008-0-NRB.json") -> SourceRecord:
        document = {
            "type": "Feature",
            "id": "facility:0-20008-0-NRB",
            "geometry": {"type": "Point", "coordinates": [36.75919, -1.30169, 1795]},
            "time": {"interval": ["1996-01-01", ".."]},
            "properties": {
                "type": "facility",
                "title": "Nairobi",
                "updated": "2025-05-04T00:00:00Z",
                "externalIds": [{"scheme": "WMO:WIGOS", "value": "0-20008-0-NRB"}],
                "contacts": [{"organization": "Kenyan Meteorological Department", "roles": ["owner"]}],
                "facilityType": "landFixed",
                "wmoRegion": "africa",
                "temporalTerritory": {"territory": ["KEN"], "dates": ["2008-12-05"]},
                "temporalProgramAffiliation": {"programAffiliation": ["GAWregional"], "dates": ["1996-01-01"]},
                "observations": [{
                    "id": "observation:369",
                    "observedVariable": 369,
                    "observedGeometryType": "point",
                    "programAffiliation": [{"programAffiliation": ["GAWregional"]}],
                    "deployments": ["deployment:current"]
                }],
                "deployments": [{
                    "id": "deployment:current",
                    "time": {"interval": ["2025-05-03", ".."]},
                    "observingMethod": 240,
                    "instrument": ["instrument:fidas"],
                    "instrumentOperatingStatus": [{"value": "operational", "time": {"interval": ["2025-05-04", ".."]}}]
                }],
                "instruments": [{"id": "instrument:fidas", "manufacturer": "PALAS", "model": "Fidas 200"}]
            }
        }
        return SourceRecord(Path(name), document, "0-20008-0-NRB", "https://example.test/nrb.json")

    def test_extract_wsi(self):
        self.assertEqual(extract_wsi(self.fixture().document), "0-20008-0-NRB")

    def test_current_open_interval(self):
        self.assertTrue(is_current({"interval": ["2025-01-01", ".."]}, date(2026, 8, 28)))
        self.assertFalse(is_current({"interval": ["2025-01-01", "2025-12-31"]}, date(2026, 8, 28)))

    def test_projection_legacy_shape(self):
        record, warnings = project_record(self.fixture(), date(2026, 8, 28))
        props = record["properties"]
        self.assertEqual(record["id"], "0-20008-0-NRB")
        self.assertEqual(props["territory"], "KEN")
        self.assertEqual(props["observationSeriesCount"], 1)
        self.assertEqual(props["currentObservationSeriesCount"], 1)
        self.assertEqual(props["currentObservedProperties"], [369])
        self.assertEqual(props["currentInstrumentModels"], ["Fidas 200"])
        self.assertEqual(props["organizations"], ["Kenyan Meteorological Department"])
        self.assertEqual(props["currentObservationOperatingStatuses"], ["operational"])
        self.assertTrue(any("non-URI" in warning for warning in warnings))

    def test_duplicate_resolution_uses_updated_date(self):
        older = self.fixture("20240101_0-20008-0-NRB.json")
        older.document["properties"]["updated"] = "2024-01-01T00:00:00Z"
        newer = self.fixture("20260101_0-20008-0-NRB.json")
        newer.document["properties"]["updated"] = "2026-01-01T00:00:00Z"
        selected, duplicates = choose_latest_by_wsi([older, newer])
        self.assertEqual(selected[0].path.name, newer.path.name)
        self.assertIn("0-20008-0-NRB", duplicates)


if __name__ == "__main__":
    unittest.main()
