import { useCallback, useEffect, useMemo, useState } from 'react';
import { fetchFacilities, type WigosRecord } from './api/records';
import { FacilitySummary } from './components/FacilitySummary';
import { PortalMap } from './map/PortalMap';

type FacetKey = 'currentProgrammes' | 'currentObservedProperties' | 'currentObservingMethods' | 'currentInstrumentModels' | 'organizations';

type FacetState = Record<FacetKey, string>;

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

function valuesFor(record: WigosRecord, key: FacetKey): Array<string | number> {
  const value = record.properties[key];
  return Array.isArray(value) ? value as Array<string | number> : [];
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

  const options = useMemo(() => {
    const result = {} as Record<FacetKey, Array<string | number>>;
    (Object.keys(initialFacets) as FacetKey[]).forEach(key => {
      result[key] = Array.from(new Set(records.flatMap(record => valuesFor(record, key).map(String))))
        .sort((a, b) => displayValue(a).localeCompare(displayValue(b)));
    });
    return result;
  }, [records]);

  const filtered = useMemo(() => records.filter(record =>
    (Object.keys(facets) as FacetKey[]).every(key => !facets[key] || valuesFor(record, key).map(String).includes(facets[key]))
  ), [records, facets]);

  useEffect(() => {
    if (selected && !filtered.some(record => record.id === selected.id)) setSelected(null);
  }, [filtered, selected]);

  const setFacet = (key: FacetKey, value: string) => setFacets(current => ({ ...current, [key]: value }));
  const hasFacets = Object.values(facets).some(Boolean);

  return (
    <main className="app-shell">
      <header>
        <div><strong>WIGOS Portal</strong><span className="poc">PoC</span></div>
        <form onSubmit={e => { e.preventDefault(); void load(); }}>
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="WSI, facility, organization, observation …" />
          <button>Search</button>
        </form>
      </header>
      <aside className="filters">
        <h2>Filters</h2>
        <p className="muted">The first PoC applies discovery facets client-side after OGC Records text/bbox retrieval. Server-side CQL2 follows once the query profile is exercised.</p>
        <Facet label="Programme" value={facets.currentProgrammes} options={options.currentProgrammes} onChange={value => setFacet('currentProgrammes', value)} />
        <Facet label="Observed property" value={facets.currentObservedProperties} options={options.currentObservedProperties} onChange={value => setFacet('currentObservedProperties', value)} />
        <Facet label="Observing method" value={facets.currentObservingMethods} options={options.currentObservingMethods} onChange={value => setFacet('currentObservingMethods', value)} />
        <Facet label="Instrument model" value={facets.currentInstrumentModels} options={options.currentInstrumentModels} onChange={value => setFacet('currentInstrumentModels', value)} />
        <Facet label="Organization" value={facets.organizations} options={options.organizations} onChange={value => setFacet('organizations', value)} />
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

function Facet({ label, value, options, onChange }: {
  label: string;
  value: string;
  options: Array<string | number>;
  onChange: (value: string) => void;
}) {
  return <label className="facet">
    <span>{label}</span>
    <select value={value} onChange={event => onChange(event.target.value)}>
      <option value="">All</option>
      {options.map(option => <option key={String(option)} value={String(option)}>{displayValue(option)}</option>)}
    </select>
  </label>;
}
