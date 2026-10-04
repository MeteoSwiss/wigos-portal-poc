from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from wmdr2_projection import (
    SourceRecord,
    WMDR2_MODEL_VERSION,
    choose_latest_by_wsi,
    extract_wsi,
    is_current,
    project_record,
)


def fixture(name: str = "20250504_0-20008-0-NRB.json") -> SourceRecord:
    document = {
        "type": "Feature",
        "id": "0-20008-0-NRB",
        "geometry": {"type": "Point", "coordinates": [36.75919, -1.30169, 1795]},
        "time": {"interval": ["1996-01-01", ".."]},
        "temporalGeometry": {
            "type": "MovingPoint",
            "coordinates": [[36.75919, -1.30169, 1795]],
            "dates": ["1996-01-01"],
        },
        "properties": {
            "type": "facility",
            "title": "Nairobi",
            "updated": "2026-09-30T00:00:00Z",
            "externalIds": [
                {
                    "scheme": "http://codes.wmo.int/wmdr/ProgramAffiliation/GAW",
                    "value": "NRB",
                }
            ],
            "additionalIds": ["0-20008-0-NRB2"],
            "contacts": [
                {
                    "organization": "Kenyan Meteorological Department",
                    "identifier": "contact:kmd",
                    "roles": ["supervisor"],
                },
                {
                    "organization": "WMO Test Centre",
                    "identifier": "contact:test-centre",
                },
            ],
            "facilityType": {
                "id": "landFixed",
                "url": "http://codes.wmo.int/wmdr/FacilityType/landFixed",
            },
            "wmoRegion": {
                "id": "africa",
                "url": "http://codes.wmo.int/wmdr/WMORegion/africa",
            },
            "territories": [
                {
                    "territory": {
                        "id": "KEN",
                        "url": "http://codes.wmo.int/wmdr/TerritoryName/KEN",
                    },
                    "dates": ["2008-12-05", ".."],
                }
            ],
            "observations": [
                {
                    "id": "369-point",
                    "observedProperty": {
                        "id": "369",
                        "url": "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/369",
                    },
                    "observedGeometry": {
                        "id": "point",
                        "url": "http://codes.wmo.int/wmdr/Geometry/point",
                    },
                    "observedFeature": {
                        "domain": {
                            "id": "atmosphere",
                            "url": "http://codes.wmo.int/wmdr/Domain/atmosphere",
                        }
                    },
                    "programAffiliations": [
                        {
                            "programAffiliation": {
                                "id": "GAWregional",
                                "url": "http://codes.wmo.int/wmdr/ProgramAffiliation/GAWregional",
                            },
                            "reportingStatus": {
                                "id": "operational",
                                "url": "http://codes.wmo.int/wmdr/ReportingStatus/operational",
                            },
                            "dates": ["1996-01-01", ".."],
                        },
                        {
                            "programAffiliation": {
                                "id": "OLD",
                                "url": "http://codes.wmo.int/wmdr/ProgramAffiliation/OLD",
                            },
                            "dates": ["1996-01-01", "2000-12-31"],
                        },
                    ],
                    "configurations": [
                        {
                            "id": "cfg-current",
                            "time": {"interval": ["2025-05-03", ".."]},
                            "observingMethod": None,
                            "operatingStatus": {
                                "id": "operational",
                                "url": "http://codes.wmo.int/wmdr/OperatingStatus/operational",
                            },
                            "instrument": "palas-fidas-200",
                            "contacts": [
                                {
                                    "ref": "contact:test-centre",
                                    "roles": ["pointOfContact"],
                                }
                            ],
                        }
                    ],
                },
                {
                    "id": "263-totalcolumn",
                    "observedProperty": {
                        "id": "263",
                        "url": "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/263",
                    },
                    "observedGeometry": {
                        "id": "totalColumn",
                        "url": "http://codes.wmo.int/wmdr/Geometry/totalColumn",
                    },
                    "observedFeature": {
                        "domain": {
                            "id": "atmosphere",
                            "url": "http://codes.wmo.int/wmdr/Domain/atmosphere",
                        }
                    },
                    "programAffiliations": [
                        {
                            "programAffiliation": {
                                "id": "GAWregional",
                                "url": "http://codes.wmo.int/wmdr/ProgramAffiliation/GAWregional",
                            }
                        }
                    ],
                    "configurations": [
                        {
                            "id": "cfg-historic",
                            "time": {"interval": ["2005-05-01", "2012-12-31"]},
                            "observingMethod": {
                                "id": "106",
                                "url": "http://codes.wmo.int/wmdr/ObservingMethodAtmosphere/106",
                            },
                        }
                    ],
                },
            ],
            "instruments": [
                {
                    "id": "palas-fidas-200",
                    "manufacturer": "PALAS",
                    "model": "Fidas 200",
                    "observingMethods": [
                        {
                            "id": "240",
                            "url": "http://codes.wmo.int/wmdr/ObservingMethodAtmosphere/240",
                        }
                    ],
                }
            ],
        },
    }
    return SourceRecord(
        Path(name), document, "0-20008-0-NRB", "https://example.test/nrb.json"
    )


def test_model_version() -> None:
    assert WMDR2_MODEL_VERSION == "0.4.0"


def test_extract_wsi_from_root_id() -> None:
    assert extract_wsi(fixture().document) == "0-20008-0-NRB"


def test_current_open_interval() -> None:
    assert is_current({"interval": ["2025-01-01", ".."]}, date(2026, 9, 30))
    assert not is_current(
        {"interval": ["2025-01-01", "2025-12-31"]}, date(2026, 9, 30)
    )


def test_projection_v040_shape() -> None:
    record, warnings = project_record(fixture(), date(2026, 9, 30))
    props = record["properties"]

    assert record["id"] == "0-20008-0-NRB"
    assert props["territory"] == "http://codes.wmo.int/wmdr/TerritoryName/KEN"
    assert props["facilityType"] == "http://codes.wmo.int/wmdr/FacilityType/landFixed"
    assert props["observationCount"] == 2
    assert props["currentObservationCount"] == 1
    assert props["currentObservedProperties"] == [
        "http://codes.wmo.int/wmdr/ObservedVariableAtmosphere/369"
    ]
    assert props["currentInstrumentModels"] == ["Fidas 200"]
    assert (
        "http://codes.wmo.int/wmdr/ObservingMethodAtmosphere/240"
        in props["currentObservingMethods"]
    )
    assert props["currentObservationOperatingStatuses"] == [
        "http://codes.wmo.int/wmdr/OperatingStatus/operational"
    ]
    assert warnings == []


def test_programme_dates_are_respected_for_current_programmes() -> None:
    record, _ = project_record(fixture(), date(2026, 9, 30))
    props = record["properties"]
    assert props["programmes"] == [
        "http://codes.wmo.int/wmdr/ProgramAffiliation/GAWregional",
        "http://codes.wmo.int/wmdr/ProgramAffiliation/OLD",
    ]
    assert props["currentProgrammes"] == [
        "http://codes.wmo.int/wmdr/ProgramAffiliation/GAWregional"
    ]


def test_generic_external_ids_are_not_rewritten_with_wsi() -> None:
    record, _ = project_record(fixture(), date(2026, 9, 30))
    assert record["properties"]["externalIds"] == [
        {
            "scheme": "http://codes.wmo.int/wmdr/ProgramAffiliation/GAW",
            "value": "NRB",
        }
    ]
    assert record["properties"]["additionalIds"] == ["0-20008-0-NRB2"]


def test_organizations_include_nested_contexts_without_flattening_contacts() -> None:
    record, _ = project_record(fixture(), date(2026, 9, 30))
    assert record["properties"]["organizations"] == [
        "Kenyan Meteorological Department",
        "WMO Test Centre",
    ]
    assert len(record["properties"]["contacts"]) == 2


def test_mobile_uses_temporal_geometry_or_facility_type() -> None:
    record, _ = project_record(fixture(), date(2026, 9, 30))
    assert record["properties"]["mobile"] is True

    source = fixture()
    source.document.pop("temporalGeometry")
    record, _ = project_record(source, date(2026, 9, 30))
    assert record["properties"]["mobile"] is False


def test_identifier_only_concept_is_preserved_and_warned() -> None:
    source = fixture()
    source.document["properties"]["observations"][0]["observedProperty"] = {"id": "369"}
    record, warnings = project_record(source, date(2026, 9, 30))
    assert "369" in record["properties"]["observedProperties"]
    assert any("observedProperties" in warning for warning in warnings)


def test_duplicate_resolution_uses_updated_date() -> None:
    older = fixture("20240101_0-20008-0-NRB.json")
    older.document["properties"]["updated"] = "2024-01-01T00:00:00Z"
    newer = fixture("20260101_0-20008-0-NRB.json")
    newer.document["properties"]["updated"] = "2026-01-01T00:00:00Z"
    selected, duplicates = choose_latest_by_wsi([older, newer])
    assert selected[0].path.name == newer.path.name
    assert "0-20008-0-NRB" in duplicates


def test_nested_contact_ref_resolves_for_organization_projection() -> None:
    record, _ = project_record(fixture(), date(2026, 9, 30))
    assert record["properties"]["organizations"] == [
        "Kenyan Meteorological Department",
        "WMO Test Centre",
    ]
