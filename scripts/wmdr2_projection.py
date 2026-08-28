from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
import re
from pathlib import Path
from typing import Any, Iterable

WSI_RE = re.compile(r"(?<![A-Za-z0-9])([0-9]+-[0-9]+-[0-9]+-[A-Za-z0-9]+)(?![A-Za-z0-9])")
DATE_PREFIX_RE = re.compile(r"^(\d{8})[_-]")


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
    """Return the machine value from common WMDR2 controlled-value shapes."""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        for key in ("value", "href", "uri", "@id", "id", "code", "notation"):
            if key in value and value[key] not in (None, ""):
                return value_of(value[key])
    return None


def values_of(value: Any) -> list[Any]:
    result: list[Any] = []
    for item in listify(value):
        if isinstance(item, dict) and len(item) == 1:
            only_value = next(iter(item.values()))
            if isinstance(only_value, list):
                result.extend(values_of(only_value))
                continue
        resolved = value_of(item)
        if resolved is not None:
            result.append(resolved)
    return unique(result)


def extract_wsi(document: dict[str, Any]) -> str | None:
    props = document.get("properties") if isinstance(document.get("properties"), dict) else {}

    for external in listify(props.get("externalIds")):
        if not isinstance(external, dict):
            continue
        scheme = str(external.get("scheme", "")).lower()
        candidate = str(external.get("value", ""))
        if "wigos" in scheme:
            match = WSI_RE.search(candidate)
            if match:
                return match.group(1)

    for candidate in (
        document.get("id"),
        props.get("id"),
        props.get("identifier"),
        props.get("wigosStationIdentifier"),
    ):
        if candidate is None:
            continue
        match = WSI_RE.search(str(candidate))
        if match:
            return match.group(1)
    return None


def is_full_facility_record(document: Any) -> bool:
    if not isinstance(document, dict):
        return False
    if document.get("type") == "FeatureCollection":
        return False
    props = document.get("properties") if isinstance(document.get("properties"), dict) else {}
    record_type = str(props.get("type", "")).lower()
    return bool(
        extract_wsi(document)
        and (
            document.get("type") == "Feature"
            or record_type in {"facility", "wigosfacility"}
        )
        and (
            record_type in {"facility", "wigosfacility"}
            or str(document.get("id", "")).startswith("facility:")
        )
    )


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
        start = value.get("start") or value.get("begin") or value.get("beginPosition")
        end = value.get("end") or value.get("endPosition") or ".."
        if start is not None:
            return start, end
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


def _container(document: dict[str, Any]) -> dict[str, Any]:
    props = document.get("properties")
    return props if isinstance(props, dict) else document


def _observations(document: dict[str, Any]) -> list[dict[str, Any]]:
    root = _container(document)
    for key in ("observationSeries", "observations", "observationSeriesCollection"):
        value = root.get(key)
        if value is not None:
            return [item for item in listify(value) if isinstance(item, dict)]
    for key in ("observationSeries", "observations"):
        value = document.get(key)
        if value is not None:
            return [item for item in listify(value) if isinstance(item, dict)]
    return []


def _legacy_deployment_index(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    root = _container(document)
    values = root.get("deployments", document.get("deployments"))
    index: dict[str, dict[str, Any]] = {}
    for item in listify(values):
        if isinstance(item, dict) and item.get("id"):
            index[str(item["id"])] = item
    return index


def _configurations(observation: dict[str, Any], deployment_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    for key in ("observingConfigurations", "observingConfiguration"):
        if key in observation:
            return [item for item in listify(observation[key]) if isinstance(item, dict)]

    capability = observation.get("observingCapabilities")
    if isinstance(capability, dict):
        for key in ("observingConfigurations", "observingConfiguration"):
            if key in capability:
                return [item for item in listify(capability[key]) if isinstance(item, dict)]

    result: list[dict[str, Any]] = []
    for ref in listify(observation.get("deployments")):
        if isinstance(ref, dict):
            result.append(ref)
        elif str(ref) in deployment_index:
            result.append(deployment_index[str(ref)])
    return result


def _observing_procedures(observation: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("observingProcedures", "observingProcedure"):
        if key in observation:
            return [item for item in listify(observation[key]) if isinstance(item, dict)]
    capability = observation.get("observingCapabilities")
    if isinstance(capability, dict):
        for key in ("observingProcedures", "observingProcedure"):
            if key in capability:
                return [item for item in listify(capability[key]) if isinstance(item, dict)]
    return []


def _programme_values(value: Any) -> list[Any]:
    """Extract programme identifiers from current and legacy WMDR2 shapes.

    WMDR2 uses the plural ``programAffiliations`` collection in current
    ObservationSeries records.  Older converter outputs used singular
    ``programAffiliation`` wrappers.  The catalogue projector accepts both
    during the transition, but emits one flat discovery array.
    """
    result: list[Any] = []
    for item in listify(value):
        if isinstance(item, dict):
            for key in (
                "programAffiliations",
                "programAffiliation",
                "programmes",
                "programme",
                "program",
                "value",
            ):
                if key in item:
                    result.extend(_programme_values(item[key]))
                    break
        else:
            result.extend(values_of(item))
    return unique(result)


def _facility_programmes(document: dict[str, Any], evaluation_date: date) -> tuple[list[Any], list[Any]]:
    root = _container(document)
    all_programmes: list[Any] = []
    current: list[Any] = []

    temporal = root.get("temporalProgramAffiliations") or root.get("temporalProgramAffiliation")
    if isinstance(temporal, dict):
        programmes = _programme_values(
            temporal.get("programAffiliations")
            or temporal.get("programAffiliation")
            or temporal.get("value")
        )
        dates = listify(temporal.get("dates"))
        all_programmes.extend(programmes)
        # Legacy temporal arrays only provide starts. Treat the latest declaration of each
        # programme as current unless a newer WMDR2 structure supplies an explicit interval.
        current.extend(programmes)

    historical = root.get("historicalProgramAffiliations") or root.get("historicalProgramAffiliation")
    for item in listify(historical):
        if not isinstance(item, dict):
            all_programmes.extend(values_of(item))
            continue
        vals = _programme_values(
            item.get("programAffiliations")
            or item.get("programAffiliation")
            or item.get("programmes")
            or item.get("programme")
            or item.get("value")
        )
        all_programmes.extend(vals)
        if is_current(item.get("time"), evaluation_date):
            current.extend(vals)

    direct = root.get("programAffiliations") or root.get("programAffiliation") or root.get("programmes")
    direct_values = _programme_values(direct)
    all_programmes.extend(direct_values)
    current.extend(direct_values)
    return unique(all_programmes), unique(current)


def _territory(document: dict[str, Any]) -> Any:
    root = _container(document)
    direct = value_of(root.get("territory"))
    if direct is not None:
        return direct
    temporal = root.get("temporalTerritory")
    if isinstance(temporal, dict):
        values = values_of(temporal.get("territory"))
        if values:
            return values[-1]
    historical = listify(root.get("historicalTerritory"))
    if historical:
        last = historical[-1]
        if isinstance(last, dict):
            return value_of(last.get("territory") or last.get("value"))
        return value_of(last)
    return None


def _contacts(document: dict[str, Any]) -> list[dict[str, Any]]:
    root = _container(document)
    contacts = [deepcopy(item) for item in listify(root.get("contacts")) if isinstance(item, dict)]
    if contacts:
        return contacts
    contacts = [deepcopy(item) for item in listify(document.get("contacts")) if isinstance(item, dict)]
    return contacts


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
    root = _container(document)
    values = root.get("instruments", document.get("instruments"))
    index: dict[str, dict[str, Any]] = {}
    for instrument in listify(values):
        if not isinstance(instrument, dict):
            continue
        key = instrument.get("id") or instrument.get("uid")
        if key:
            index[str(key)] = instrument
    return index


def _instrument_refs(configuration: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for raw in listify(configuration.get("instrument") or configuration.get("instruments")):
        if isinstance(raw, str):
            result.append(raw)
        elif isinstance(raw, dict):
            candidate = raw.get("id") or raw.get("href") or raw.get("ref") or raw.get("instrument")
            if candidate:
                result.append(str(candidate))
    return unique(result)


def _operating_statuses(configuration: dict[str, Any], evaluation_date: date) -> list[Any]:
    direct = values_of(configuration.get("operatingStatus"))
    if direct:
        return direct
    legacy = configuration.get("instrumentOperatingStatus")
    result: list[Any] = []
    for status in listify(legacy):
        if not isinstance(status, dict):
            result.extend(values_of(status))
        elif is_current(status.get("time"), evaluation_date):
            result.extend(values_of(status.get("value")))
    return unique(result)


def _record_link(source: SourceRecord) -> list[dict[str, Any]]:
    if not source.source_url:
        return []
    return [{
        "href": source.source_url,
        "rel": "canonical",
        "type": "application/geo+json",
        "title": "Canonical WMDR2 JSON",
    }]


def project_record(source: SourceRecord, evaluation_date: date | None = None) -> tuple[dict[str, Any], list[str]]:
    evaluation_date = evaluation_date or date.today()
    document = source.document
    root = _container(document)
    warnings: list[str] = []

    contacts = _contacts(document)
    programmes, current_programmes = _facility_programmes(document, evaluation_date)
    deployment_index = _legacy_deployment_index(document)
    instruments = _instrument_index(document)
    observations = _observations(document)

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
    observation_programmes: list[Any] = []
    current_observation_programmes: list[Any] = []
    current_series_count = 0

    for observation in observations:
        observed = value_of(observation.get("observedProperty"))
        if observed is None:
            observed = value_of(observation.get("observedVariable"))
        geometry = value_of(observation.get("observedGeometry"))
        if geometry is None:
            geometry = value_of(observation.get("observedGeometryType"))
        if observed is not None:
            observed_properties.append(observed)
        if geometry is not None:
            observed_geometries.append(geometry)

        obs_programmes = _programme_values(
            observation.get("programAffiliations")
            or observation.get("programAffiliation")
            or observation.get("programmes")
        )
        observation_programmes.extend(obs_programmes)
        configs = _configurations(observation, deployment_index)
        current_configs = [cfg for cfg in configs if is_current(cfg.get("time"), evaluation_date)]
        if current_configs:
            current_series_count += 1
            if observed is not None:
                current_observed_properties.append(observed)
            current_observation_programmes.extend(obs_programmes)

        procedures = _observing_procedures(observation)
        for procedure in procedures:
            observing_methods.extend(values_of(procedure.get("observingMethod")))
            if is_current(procedure.get("time"), evaluation_date):
                current_observing_methods.extend(values_of(procedure.get("observingMethod")))

        for configuration in configs:
            methods = values_of(configuration.get("observingMethod"))
            observing_methods.extend(methods)
            refs = _instrument_refs(configuration)
            for ref in refs:
                instrument = instruments.get(ref)
                if not instrument:
                    continue
                manufacturer = instrument.get("manufacturer")
                model = instrument.get("model")
                if manufacturer:
                    instrument_manufacturers.append(str(manufacturer))
                if model:
                    instrument_models.append(str(model))

            if configuration in current_configs:
                current_observing_methods.extend(methods)
                current_statuses.extend(_operating_statuses(configuration, evaluation_date))
                for ref in refs:
                    instrument = instruments.get(ref)
                    if not instrument:
                        continue
                    manufacturer = instrument.get("manufacturer")
                    model = instrument.get("model")
                    if manufacturer:
                        current_instrument_manufacturers.append(str(manufacturer))
                    if model:
                        current_instrument_models.append(str(model))

    programmes = unique([*programmes, *observation_programmes])
    current_programmes = unique([*current_programmes, *current_observation_programmes])

    # Surface values that are not yet URIs rather than fabricating identifiers. This is
    # expected for some legacy converter outputs and will disappear as WMDR2 examples
    # adopt canonical code-list URLs.
    for field_name, values in (
        ("programmes", programmes),
        ("observedProperties", observed_properties),
        ("observingMethods", observing_methods),
    ):
        for value in unique(values):
            if isinstance(value, (int, float)) or (isinstance(value, str) and not value.startswith(("http://", "https://"))):
                warnings.append(f"{field_name}: non-URI controlled value preserved as-is: {value}")

    external_ids = deepcopy(listify(root.get("externalIds")))
    if not any(isinstance(item, dict) and str(item.get("value")) == source.wsi for item in external_ids):
        external_ids.insert(0, {"scheme": "WMO:WIGOS", "value": source.wsi})

    properties: dict[str, Any] = {
        "type": "wigosFacility",
        "title": root.get("title") or source.wsi,
        "description": root.get("description"),
        "externalIds": external_ids,
        "contacts": contacts,
        "facilityType": value_of(root.get("facilityType")),
        "territory": _territory(document),
        "wmoRegion": value_of(root.get("wmoRegion")),
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
        "organizations": _organizations(contacts),
        "observationSeriesCount": len(observations),
        "currentObservationSeriesCount": current_series_count,
        "mobile": str(value_of(root.get("facilityType")) or "").lower() in {
            "landmobile", "seamobile", "airmobile", "mobile", "moving"
        } or (isinstance(document.get("geometry"), dict) and document["geometry"].get("type") == "MovingPoint"),
        "sourceFile": source.path.name,
    }
    if source.source_url:
        properties["wmdr2Url"] = source.source_url

    # Remove empty optional values but keep explicit zero/false values and empty arrays for
    # stable queryable fields.
    stable_arrays = {
        "programmes", "currentProgrammes", "observedProperties", "currentObservedProperties",
        "observedGeometries", "observingMethods", "currentObservingMethods",
        "instrumentManufacturers", "currentInstrumentManufacturers", "instrumentModels",
        "currentInstrumentModels", "currentObservationOperatingStatuses", "organizations", "contacts",
    }
    properties = {
        key: value for key, value in properties.items()
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
