from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
import re
from pathlib import Path
from typing import Any, Iterable

WMDR2_MODEL_VERSION = "0.4.0"

WSI_RE = re.compile(r"(?<![A-Za-z0-9])([0-9]+-[0-9]+-[0-9]+-[A-Za-z0-9]+)(?![A-Za-z0-9])")
DATE_PREFIX_RE = re.compile(r"^(\d{8})[_-]")
URI_PREFIXES = ("http://", "https://")


@dataclass(frozen=True)
class SourceRecord:
    path: Path
    document: dict[str, Any]
    wsi: str
    source_url: str | None = None


def listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def unique(values: Iterable[Any]) -> list[Any]:
    out: list[Any] = []
    seen: set[str] = set()
    for value in values:
        if value is None or value == "":
            continue
        marker = repr(value)
        if marker not in seen:
            seen.add(marker)
            out.append(value)
    return out


def value_of(value: Any) -> Any:
    """Return a discovery value from a WMDR2 v0.4.0 Concept-like value.

    WMDR2 v0.4.0 uses compact notation in ``id`` and, where known, the
    canonical controlled-vocabulary URI in ``url``.  Discovery/query fields
    prefer the URI so the machine value remains globally unambiguous.  Compact
    ``id`` is retained only as a fallback for identifier-only Concepts or
    legacy scalar input.
    """
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        for key in ("url", "href", "uri", "@id", "id", "code", "notation", "value"):
            if key in value and value[key] not in (None, ""):
                return value_of(value[key])
    return None


def concept_id(value: Any) -> str | None:
    """Return the compact Concept id, when available, for business logic."""
    if isinstance(value, dict):
        raw = value.get("id")
        if raw not in (None, ""):
            return str(raw)
    resolved = value_of(value)
    if isinstance(resolved, str) and resolved:
        return resolved.rstrip("/").split("/")[-1]
    if resolved is not None:
        return str(resolved)
    return None


def values_of(value: Any) -> list[Any]:
    result: list[Any] = []
    for item in listify(value):
        resolved = value_of(item)
        if resolved is not None:
            result.append(resolved)
    return unique(result)


def extract_wsi(document: dict[str, Any]) -> str | None:
    """Extract the primary WSI.

    In WMDR2 v0.4.0 the root Feature ``id`` is the primary WSI.  A small
    fallback is kept for malformed/imported records, but the projector never
    fabricates a WSI in ``externalIds``.
    """
    for candidate in (
        document.get("id"),
        document.get("properties", {}).get("id") if isinstance(document.get("properties"), dict) else None,
    ):
        if candidate is None:
            continue
        match = WSI_RE.search(str(candidate))
        if match:
            return match.group(1)
    return None


def is_full_facility_record(document: Any) -> bool:
    if not isinstance(document, dict) or document.get("type") != "Feature":
        return False
    props = document.get("properties")
    if not isinstance(props, dict):
        return False
    return bool(extract_wsi(document) and str(props.get("type", "")).lower() == "facility")


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value or value == "..":
        return None
    text = value.strip()
    try:
        if len(text) == 10:
            return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _record_recency(source: SourceRecord) -> tuple[datetime, str]:
    props = source.document.get("properties", {})
    if isinstance(props, dict):
        for key in ("updated", "created"):
            parsed = _parse_datetime(props.get(key))
            if parsed:
                return parsed, source.path.name
    match = DATE_PREFIX_RE.match(source.path.name)
    if match:
        parsed = datetime.strptime(match.group(1), "%Y%m%d").replace(tzinfo=timezone.utc)
        return parsed, source.path.name
    return datetime.min.replace(tzinfo=timezone.utc), source.path.name


def choose_latest_by_wsi(records: Iterable[SourceRecord]) -> tuple[list[SourceRecord], dict[str, list[str]]]:
    grouped: dict[str, list[SourceRecord]] = {}
    for record in records:
        grouped.setdefault(record.wsi, []).append(record)

    selected: list[SourceRecord] = []
    duplicates: dict[str, list[str]] = {}
    for wsi, candidates in grouped.items():
        ordered = sorted(candidates, key=_record_recency, reverse=True)
        selected.append(ordered[0])
        if len(ordered) > 1:
            duplicates[wsi] = [item.path.name for item in ordered]
    return sorted(selected, key=lambda item: item.wsi), duplicates


def _interval(value: Any) -> tuple[Any, Any] | None:
    if isinstance(value, dict):
        raw = value.get("interval")
        if isinstance(raw, list) and len(raw) >= 2:
            return raw[0], raw[1]
    if isinstance(value, list) and len(value) >= 2:
        return value[0], value[1]
    return None


def is_current(time_value: Any, evaluation_date: date) -> bool:
    interval = _interval(time_value)
    if interval is None:
        return False
    start_raw, end_raw = interval
    start = _parse_datetime(str(start_raw)) if start_raw not in (None, "..") else None
    end = _parse_datetime(str(end_raw)) if end_raw not in (None, "..") else None
    point = datetime.combine(evaluation_date, datetime.min.time(), tzinfo=timezone.utc)
    return (start is None or start <= point) and (end is None or point <= end)


def _dates_current(dates: Any, evaluation_date: date) -> bool:
    """Evaluate official WMDR2 ``dates`` as an interval when present.

    Missing dates mean that the source supplied no temporal qualifier for that
    occurrence; the occurrence therefore remains applicable rather than being
    treated as demonstrably historical.
    """
    if dates in (None, []):
        return True
    return is_current({"interval": dates}, evaluation_date)


def _container(document: dict[str, Any]) -> dict[str, Any]:
    props = document.get("properties")
    return props if isinstance(props, dict) else {}


def _observations(document: dict[str, Any]) -> list[dict[str, Any]]:
    value = _container(document).get("observations")
    return [item for item in listify(value) if isinstance(item, dict)]


def _configurations(observation: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in listify(observation.get("configurations")) if isinstance(item, dict)]


def _observing_procedures(observation: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in listify(observation.get("observingProcedures")) if isinstance(item, dict)]


def _programme_values(observation: dict[str, Any]) -> tuple[list[Any], list[tuple[Any, Any]]]:
    """Return all programmes and ``(value, dates)`` pairs for an Observation."""
    all_values: list[Any] = []
    temporal_values: list[tuple[Any, Any]] = []
    for item in listify(observation.get("programAffiliations")):
        if not isinstance(item, dict):
            continue
        resolved = value_of(item.get("programAffiliation"))
        if resolved is None:
            continue
        all_values.append(resolved)
        temporal_values.append((resolved, item.get("dates")))
    return unique(all_values), temporal_values


def _territory(document: dict[str, Any], evaluation_date: date) -> Any:
    territories = [item for item in listify(_container(document).get("territories")) if isinstance(item, dict)]
    if not territories:
        return None

    current = [item for item in territories if _dates_current(item.get("dates"), evaluation_date)]
    selected = current[-1] if current else territories[-1]
    return value_of(selected.get("territory"))


def _contacts(document: dict[str, Any]) -> list[dict[str, Any]]:
    return [deepcopy(item) for item in listify(_container(document).get("contacts")) if isinstance(item, dict)]


def _all_contact_occurrences(document: dict[str, Any]) -> list[dict[str, Any]]:
    result = _contacts(document)
    for observation in _observations(document):
        result.extend(deepcopy(item) for item in listify(observation.get("contacts")) if isinstance(item, dict))
        for configuration in _configurations(observation):
            result.extend(deepcopy(item) for item in listify(configuration.get("contacts")) if isinstance(item, dict))
    return result


def _organizations(contacts: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for contact in contacts:
        organization = contact.get("organization")
        if isinstance(organization, str) and organization.strip():
            values.append(organization.strip())
        elif isinstance(organization, dict):
            label = organization.get("name") or organization.get("title") or organization.get("value")
            if label:
                values.append(str(label).strip())
    return unique(values)


def _instrument_index(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for instrument in listify(_container(document).get("instruments")):
        if isinstance(instrument, dict) and instrument.get("id") not in (None, ""):
            index[str(instrument["id"])] = instrument
    return index


def _instrument_refs(configuration: dict[str, Any]) -> list[str]:
    raw = configuration.get("instrument")
    if raw is None:
        return []
    if isinstance(raw, (str, int)):
        return [str(raw)]
    if isinstance(raw, dict):
        candidate = raw.get("id") or raw.get("href") or raw.get("ref")
        return [str(candidate)] if candidate not in (None, "") else []
    return []


def _instrument_methods(instrument: dict[str, Any]) -> list[Any]:
    return values_of(instrument.get("observingMethods"))


def _operating_statuses(configuration: dict[str, Any]) -> list[Any]:
    return values_of(configuration.get("operatingStatus"))


def _record_link(source: SourceRecord) -> list[dict[str, Any]]:
    if not source.source_url:
        return []
    return [{
        "href": source.source_url,
        "rel": "canonical",
        "type": "application/geo+json",
        "title": "Canonical WMDR2 JSON",
    }]


def _warn_non_uri(field_name: str, values: Iterable[Any], warnings: list[str]) -> None:
    for value in unique(values):
        if isinstance(value, (int, float)) or (
            isinstance(value, str) and not value.startswith(URI_PREFIXES)
        ):
            warnings.append(
                f"{field_name}: controlled value has no canonical URI; compact/legacy value preserved: {value}"
            )


def project_record(source: SourceRecord, evaluation_date: date | None = None) -> tuple[dict[str, Any], list[str]]:
    evaluation_date = evaluation_date or date.today()
    document = source.document
    root = _container(document)
    warnings: list[str] = []

    contacts = _contacts(document)
    all_contacts = _all_contact_occurrences(document)
    instruments = _instrument_index(document)
    observations = _observations(document)

    programmes: list[Any] = []
    current_programmes: list[Any] = []
    observed_properties: list[Any] = []
    current_observed_properties: list[Any] = []
    observed_geometries: list[Any] = []
    observing_methods: list[Any] = []
    current_observing_methods: list[Any] = []
    instrument_manufacturers: list[str] = []
    current_instrument_manufacturers: list[str] = []
    instrument_models: list[str] = []
    current_instrument_models: list[str] = []
    current_statuses: list[Any] = []
    current_observation_count = 0

    for observation in observations:
        observed = value_of(observation.get("observedProperty"))
        geometry = value_of(observation.get("observedGeometry"))
        if observed is not None:
            observed_properties.append(observed)
        if geometry is not None:
            observed_geometries.append(geometry)

        obs_programmes, temporal_programmes = _programme_values(observation)
        programmes.extend(obs_programmes)

        configs = _configurations(observation)
        current_configs = [cfg for cfg in configs if is_current(cfg.get("time"), evaluation_date)]
        observation_is_current = bool(current_configs)
        if observation_is_current:
            current_observation_count += 1
            if observed is not None:
                current_observed_properties.append(observed)
            current_programmes.extend(
                value for value, dates in temporal_programmes if _dates_current(dates, evaluation_date)
            )

        for procedure in _observing_procedures(observation):
            procedure_methods = values_of(procedure.get("observingMethod"))
            observing_methods.extend(procedure_methods)
            if is_current(procedure.get("time"), evaluation_date):
                current_observing_methods.extend(procedure_methods)

        for configuration in configs:
            config_methods = values_of(configuration.get("observingMethod"))
            observing_methods.extend(config_methods)

            refs = _instrument_refs(configuration)
            referenced_instruments = [instruments[ref] for ref in refs if ref in instruments]
            for instrument in referenced_instruments:
                instrument_methods = _instrument_methods(instrument)
                observing_methods.extend(instrument_methods)
                manufacturer = instrument.get("manufacturer")
                model = instrument.get("model")
                if manufacturer:
                    instrument_manufacturers.append(str(manufacturer))
                if model:
                    instrument_models.append(str(model))

            if configuration in current_configs:
                current_observing_methods.extend(config_methods)
                current_statuses.extend(_operating_statuses(configuration))
                for instrument in referenced_instruments:
                    current_observing_methods.extend(_instrument_methods(instrument))
                    manufacturer = instrument.get("manufacturer")
                    model = instrument.get("model")
                    if manufacturer:
                        current_instrument_manufacturers.append(str(manufacturer))
                    if model:
                        current_instrument_models.append(str(model))

    facility_type = value_of(root.get("facilityType"))
    wmo_region = value_of(root.get("wmoRegion"))
    territory = _territory(document, evaluation_date)

    for field_name, values in (
        ("facilityType", [facility_type]),
        ("territory", [territory]),
        ("wmoRegion", [wmo_region]),
        ("programmes", programmes),
        ("observedProperties", observed_properties),
        ("observedGeometries", observed_geometries),
        ("observingMethods", observing_methods),
        ("currentObservationOperatingStatuses", current_statuses),
    ):
        _warn_non_uri(field_name, values, warnings)

    facility_type_id = (concept_id(root.get("facilityType")) or "").lower()
    temporal_geometry = document.get("temporalGeometry")
    temporal_geometry_type = (
        str(temporal_geometry.get("type", "")).lower()
        if isinstance(temporal_geometry, dict)
        else ""
    )
    mobile = facility_type_id in {
        "landmobile",
        "seamobile",
        "airmobile",
        "mobile",
        "moving",
    } or temporal_geometry_type == "movingpoint"

    properties: dict[str, Any] = {
        "type": "wigosFacility",
        "title": root.get("title") or source.wsi,
        "description": root.get("description"),
        # Preserve generic OGC externalIds exactly. Root id is the primary WSI;
        # WMDR2 additionalIds contains further WSIs where present.
        "externalIds": deepcopy(listify(root.get("externalIds"))),
        "additionalIds": deepcopy(listify(root.get("additionalIds"))),
        "contacts": contacts,
        "facilityType": facility_type,
        "territory": territory,
        "wmoRegion": wmo_region,
        "programmes": unique(programmes),
        "currentProgrammes": unique(current_programmes),
        "observedProperties": unique(observed_properties),
        "currentObservedProperties": unique(current_observed_properties),
        "observedGeometries": unique(observed_geometries),
        "observingMethods": unique(observing_methods),
        "currentObservingMethods": unique(current_observing_methods),
        "instrumentManufacturers": unique(instrument_manufacturers),
        "currentInstrumentManufacturers": unique(current_instrument_manufacturers),
        "instrumentModels": unique(instrument_models),
        "currentInstrumentModels": unique(current_instrument_models),
        "currentObservationOperatingStatuses": unique(current_statuses),
        "organizations": _organizations(all_contacts),
        "observationCount": len(observations),
        "currentObservationCount": current_observation_count,
        "mobile": mobile,
        "sourceFile": source.path.name,
    }
    if source.source_url:
        properties["wmdr2Url"] = source.source_url

    stable_arrays = {
        "externalIds",
        "additionalIds",
        "programmes",
        "currentProgrammes",
        "observedProperties",
        "currentObservedProperties",
        "observedGeometries",
        "observingMethods",
        "currentObservingMethods",
        "instrumentManufacturers",
        "currentInstrumentManufacturers",
        "instrumentModels",
        "currentInstrumentModels",
        "currentObservationOperatingStatuses",
        "organizations",
        "contacts",
    }
    properties = {
        key: value
        for key, value in properties.items()
        if value not in (None, "") and (value != [] or key in stable_arrays)
    }

    record = {
        "type": "Feature",
        "id": source.wsi,
        "geometry": deepcopy(document.get("geometry")),
        "time": deepcopy(document.get("time")),
        "properties": properties,
        "links": _record_link(source),
    }
    return record, unique(warnings)
