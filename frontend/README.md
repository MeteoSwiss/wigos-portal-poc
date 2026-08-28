# Frontend

TypeScript/React/Vite/OpenLayers Portal frontend.

The current local slice implements:

- global Mollweide, Arctic stereographic and Antarctic stereographic views;
- projection switching without mutating/reprojecting source features in place;
- point hover summaries and click selection;
- geographic box queries through OGC API - Records;
- free-text `q` search through OGC API - Records;
- initial programme/observation/method/instrument/organization facets;
- compact facility summary including organizations and contacts.

For the first PoC, facets are applied client-side to the OGC Records result set. This keeps the initial UI test independent from the final CQL2 expressions for array-valued WIGOS queryables.

Local development:

```bash
npm install
npm run dev
```

The default catalogue URL is `http://localhost:5000`. Override it with `VITE_RECORDS_API_BASE` when needed.
