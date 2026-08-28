export interface Contact {
  name?: string;
  organization?: string | Record<string, unknown>;
  roles?: string[];
  emails?: Array<{ value?: string } | string>;
  phones?: Array<{ value?: string } | string>;
  [key: string]: unknown;
}

export interface WigosRecordProperties {
  type?: string;
  title?: string;
  description?: string;
  territory?: string;
  wmoRegion?: string;
  facilityType?: string;
  programmes?: Array<string | number>;
  currentProgrammes?: Array<string | number>;
  observedProperties?: Array<string | number>;
  currentObservedProperties?: Array<string | number>;
  observedGeometries?: Array<string | number>;
  observingMethods?: Array<string | number>;
  currentObservingMethods?: Array<string | number>;
  instrumentManufacturers?: string[];
  currentInstrumentManufacturers?: string[];
  instrumentModels?: string[];
  currentInstrumentModels?: string[];
  currentObservationOperatingStatuses?: Array<string | number>;
  organizations?: string[];
  contacts?: Contact[];
  observationSeriesCount?: number;
  currentObservationSeriesCount?: number;
  sourceFile?: string;
  wmdr2Url?: string;
  [key: string]: unknown;
}

export interface WigosRecord {
  type: 'Feature';
  id: string;
  geometry: Record<string, unknown> | null;
  properties: WigosRecordProperties;
  time?: Record<string, unknown> | null;
  links?: Array<{ href: string; rel?: string; type?: string; title?: string }>;
}

interface RecordCollection {
  type: 'FeatureCollection';
  features: WigosRecord[];
  numberMatched?: number;
  numberReturned?: number;
}

const base = (import.meta.env.VITE_RECORDS_API_BASE || 'http://localhost:5000').replace(/\/$/, '');

export async function fetchFacilities(params: URLSearchParams = new URLSearchParams()): Promise<RecordCollection> {
  if (!params.has('limit')) params.set('limit', '1000');
  const url = `${base}/collections/wigos-facilities/items?${params.toString()}`;
  const response = await fetch(url, { headers: { Accept: 'application/geo+json, application/json' } });
  if (!response.ok) throw new Error(`Catalogue request failed: ${response.status} ${response.statusText}`);
  return response.json();
}
