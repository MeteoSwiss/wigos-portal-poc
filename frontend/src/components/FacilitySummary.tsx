import type { Contact, WigosRecord } from '../api/records';

function tail(value?: string | number) {
  if (value === undefined || value === null || value === '') return '—';
  const text = String(value);
  const parts = text.split('/');
  return parts[parts.length - 1] || text;
}

function list(values?: Array<string | number>) {
  return values?.map(tail).join(', ') || '—';
}

function emailValues(contact: Contact) {
  return (contact.emails || []).map(item => typeof item === 'string' ? item : item.value).filter(Boolean).join(', ');
}

export function FacilitySummary({ record }: { record: WigosRecord | null }) {
  if (!record) return <div className="empty-panel">Select a facility to see its compact report.</div>;
  const p = record.properties;
  return (
    <article className="facility-summary">
      <h2>{p.title || record.id}</h2>
      <div className="wsi">{record.id}</div>
      {p.description && <p>{p.description}</p>}
      <dl>
        <dt>Territory</dt><dd>{tail(p.territory)}</dd>
        <dt>WMO Region</dt><dd>{tail(p.wmoRegion)}</dd>
        <dt>Facility type</dt><dd>{tail(p.facilityType)}</dd>
        <dt>Observation series</dt><dd>{p.observationSeriesCount ?? '—'}</dd>
        <dt>Current series</dt><dd>{p.currentObservationSeriesCount ?? '—'}</dd>
      </dl>
      <h3>Current programmes</h3>
      <div>{list(p.currentProgrammes)}</div>
      <h3>Current observations</h3>
      <div>{list(p.currentObservedProperties)}</div>
      <h3>Current observing methods</h3>
      <div>{list(p.currentObservingMethods)}</div>
      <h3>Current instruments</h3>
      <div>{p.currentInstrumentModels?.join(', ') || '—'}</div>
      <h3>Organizations</h3>
      <div>{p.organizations?.join(', ') || '—'}</div>
      {p.contacts && p.contacts.length > 0 && <>
        <h3>Contacts</h3>
        <ul className="contact-list">
          {p.contacts.map((contact, index) => <li key={`${contact.name || contact.organization || 'contact'}-${index}`}>
            <strong>{contact.name || (typeof contact.organization === 'string' ? contact.organization : 'Contact')}</strong>
            {contact.name && typeof contact.organization === 'string' && <span>{contact.organization}</span>}
            {contact.roles && <span>{contact.roles.join(', ')}</span>}
            {emailValues(contact) && <span>{emailValues(contact)}</span>}
          </li>)}
        </ul>
      </>}
      <div className="report-links">
        {p.wmdr2Url && <a href={p.wmdr2Url} target="_blank" rel="noreferrer">View canonical WMDR2 JSON</a>}
      </div>
    </article>
  );
}
