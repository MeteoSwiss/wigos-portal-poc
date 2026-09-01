import { useCallback, useEffect, useMemo, useState } from 'react';
import { fetchFacilities, type WigosRecord } from './api/records';
import { FacilitySummary } from './components/FacilitySummary';
import { PortalMap } from './map/PortalMap';

type FacetKey = 'currentProgrammes' | 'currentObservedProperties' | 'currentObservingMethods' | 'currentInstrumentModels' | 'organizations';

type FacetState = Record<FacetKey, string>;

type FacetOption = {
  value: string;
  count: number;
};

const facetKeys: FacetKey[] = [
  'currentProgrammes',
  'currentObservedProperties',
  'currentObservingMethods',
  'currentInstrumentModels',
  'organizations',
];

const initialFacets: FacetState = {
  currentProgrammes: '',
  currentObservedProperties: '',
  currentObservingMethods: '',
  currentInstrumentModels: '',
  organizations: '',
};

function displayValue(value: string | number) {
  const text = String(value);
  const parts = text.split('/');
  return parts[parts.length - 1] || text;
}

function valuesFor(record: WigosRecord, key: FacetKey): string[] {
  const value = record.properties[key];
  return Array.isArray(value) ? value.map(String) : [];
}

function matchesFacets(record: WigosRecord, facets: FacetState, except?: FacetKey) {
  return facetKeys.every(key => {
    if (key === except || !facets[key]) return true;
    return valuesFor(record, key).includes(facets[key]);
  });
}

function normalizeFacets(records: WigosRecord[], facets: FacetState): FacetState {
  let next = { ...facets };
  let changed = true;

  // A query/bbox refresh can remove values that were selected previously.
  // Remove only selections that are no longer compatible with the other
  // active facets in the current result set.
  while (changed) {
    changed = false;
    for (const key of facetKeys) {
      const selected = next[key];
      if (!selected) continue;
      const compatible = records
        .filter(record => matchesFacets(record, next, key))
        .some(record => valuesFor(record, key).includes(selected));
      if (!compatible) {
        next = { ...next, [key]: '' };
        changed = true;
      }
    }
  }
  return next;
}

export default function App() {
  const [records, setRecords] = useState<WigosRecord[]>([]);
  const [selected, setSelected] = useState<WigosRecord | null>(null);
  const [query, setQuery] = useState('');
  const [bbox, setBbox] = useState<number[] | null>(null);
  const [facets, setFacets] = useState<FacetState>(initialFacets);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const params = new URLSearchParams();
    if (query.trim()) params.set('q', query.trim());
    if (bbox) params.set('bbox', bbox.join(','));
    try {
      setError(null);
      const data = await fetchFacilities(params);
      setRecords(data.features || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [query, bbox]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    setFacets(current => normalizeFacets(records, current));
  }, [records]);

  const options = useMemo(() => {
    const result = {} as Record<FacetKey, FacetOption[]>;

    for (const key of facetKeys) {
      const counts = new Map<string, number>();
      const compatibleRecords = records.filter(record => matchesFacets(record, facets, key));

      for (const record of compatibleRecords) {
        // Count a facility only once per option even if malformed input contains
        // the same value more than once in the corresponding array.
        for (const value of new Set(valuesFor(record, key))) {
          counts.set(value, (counts.get(value) || 0) + 1);
        }
      }

      result[key] = Array.from(counts, ([value, count]) => ({ value, count }))
        .sort((a, b) => displayValue(a.value).localeCompare(displayValue(b.value)));
    }

    return result;
  }, [records, facets]);

  const filtered = useMemo(
    () => records.filter(record => matchesFacets(record, facets)),
    [records, facets],
  );

  useEffect(() => {
    if (selected && !filtered.some(record => record.id === selected.id)) setSelected(null);
  }, [filtered, selected]);

  const setFacet = (key: FacetKey, value: string) => {
    setFacets(current => normalizeFacets(records, { ...current, [key]: value }));
  };
  const hasFacets = Object.values(facets).some(Boolean);

  return (
    <main className="app-shell">
      <header>
        <div className="brand">
          <strong>WIGOS Portal</strong>
          <span className="poc">PoC</span>
          <a
            href="https://github.com/MeteoSwiss/wigos-portal-poc#readme"
            style={{ marginLeft: '12px', fontSize: '.88rem', color: '#1d6f8a' }}
            target="_blank"
            rel="noreferrer"
          >
            Documentation
          </a>
        </div>
        <form onSubmit={e => { e.preventDefault(); void load(); }}>
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="WSI, facility, organization, observation …" />
          <button>Search</button>
        </form>
      </header>
      <aside className="filters">
        <h2>Filters</h2>
        <p className="muted">Selectors are faceted: each list shows only values compatible with the other active filters. Counts indicate the number of facilities for each available choice.</p>
        <Facet label="Programme" value={facets.currentProgrammes} options={options.currentProgrammes} total={records.filter(record => matchesFacets(record, facets, 'currentProgrammes')).length} onChange={value => setFacet('currentProgrammes', value)} />
        <Facet label="Observed property" value={facets.currentObservedProperties} options={options.currentObservedProperties} total={records.filter(record => matchesFacets(record, facets, 'currentObservedProperties')).length} onChange={value => setFacet('currentObservedProperties', value)} />
        <Facet label="Observing method" value={facets.currentObservingMethods} options={options.currentObservingMethods} total={records.filter(record => matchesFacets(record, facets, 'currentObservingMethods')).length} onChange={value => setFacet('currentObservingMethods', value)} />
        <Facet label="Instrument model" value={facets.currentInstrumentModels} options={options.currentInstrumentModels} total={records.filter(record => matchesFacets(record, facets, 'currentInstrumentModels')).length} onChange={value => setFacet('currentInstrumentModels', value)} />
        <Facet label="Organization" value={facets.organizations} options={options.organizations} total={records.filter(record => matchesFacets(record, facets, 'organizations')).length} onChange={value => setFacet('organizations', value)} />
        {(bbox || hasFacets) && <div className="filter-actions">
          {bbox && <button onClick={() => setBbox(null)}>Clear map box</button>}
          {hasFacets && <button onClick={() => setFacets(initialFacets)}>Clear facets</button>}
        </div>}
        <div className="result-count">{filtered.length} of {records.length} facilities</div>
        {error && <div className="error">{error}</div>}
      </aside>
      <PortalMap records={filtered} onSelect={setSelected} onBox={setBbox} />
      <aside className="report"><FacilitySummary record={selected} /></aside>
    </main>
  );
}

function Facet({ label, value, options, total, onChange }: {
  label: string;
  value: string;
  options: FacetOption[];
  total: number;
  onChange: (value: string) => void;
}) {
  return <label className="facet">
    <span>{label}</span>
    <select value={value} onChange={event => onChange(event.target.value)}>
      <option value="">All ({total})</option>
      {options.map(option => (
        <option key={option.value} value={option.value}>
          {displayValue(option.value)} ({option.count})
        </option>
      ))}
    </select>
  </label>;
}
