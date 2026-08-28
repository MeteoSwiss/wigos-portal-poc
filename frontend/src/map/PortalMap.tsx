import { useEffect, useRef, useState } from 'react';
import Feature from 'ol/Feature';
import OlMap from 'ol/Map';
import Overlay from 'ol/Overlay';
import View from 'ol/View';
import GeoJSON from 'ol/format/GeoJSON';
import Polygon from 'ol/geom/Polygon';
import DragBox from 'ol/interaction/DragBox';
import Graticule from 'ol/layer/Graticule';
import VectorLayer from 'ol/layer/Vector';
import { transform, transformExtent } from 'ol/proj';
import VectorSource from 'ol/source/Vector';
import { Circle as CircleStyle, Fill, Stroke, Style } from 'ol/style';
import type { WigosRecord } from '../api/records';
import { defaultView, projectionLabels, type PortalProjection } from './projections';
import './basemap.css';

const stationSource = new VectorSource({ wrapX: false });
const basemapSource = new VectorSource({ wrapX: false });
const frameSource = new VectorSource({ wrapX: false });

const basemapLayer = new VectorLayer({
  source: basemapSource,
  style: new Style({
    fill: new Fill({ color: 'rgba(239, 241, 236, 1)' }),
    stroke: new Stroke({ color: 'rgba(113, 126, 126, 0.72)', width: 0.7 }),
  }),
});

const frameLayer = new VectorLayer({
  source: frameSource,
  style: new Style({
    fill: new Fill({ color: 'rgba(0, 0, 0, 0)' }),
    stroke: new Stroke({ color: 'rgba(82, 99, 104, 0.9)', width: 1.15 }),
  }),
});

const graticuleLayer = new Graticule({
  strokeStyle: new Stroke({ color: 'rgba(94, 118, 125, 0.32)', width: 0.65 }),
  showLabels: false,
  wrapX: false,
  targetSize: 150,
});

const stationLayer = new VectorLayer({
  source: stationSource,
  style: new Style({
    image: new CircleStyle({
      radius: 4.2,
      fill: new Fill({ color: '#1d6f8a' }),
      stroke: new Stroke({ color: '#ffffff', width: 1 }),
    }),
  }),
});

type GeoJsonObject = Record<string, unknown>;

function tail(value?: string) {
  if (!value) return '';
  const parts = value.split('/');
  return parts[parts.length - 1] || value;
}

function projectionFrame(code: PortalProjection) {
  const geographicRing: number[][] = [];

  if (code === 'ESRI:54009') {
    for (let lat = -89.9; lat <= 89.9; lat += 2) geographicRing.push([180, lat]);
    for (let lat = 89.9; lat >= -89.9; lat -= 2) geographicRing.push([-180, lat]);
  } else {
    const latitude = code === 'EPSG:3995' ? 20 : -20;
    for (let lon = -180; lon <= 180; lon += 3) geographicRing.push([lon, latitude]);
  }

  geographicRing.push(geographicRing[0]);
  const projected = geographicRing.map(coordinate => transform(coordinate, 'EPSG:4326', code));
  return new Feature(new Polygon([projected]));
}

function basemapFeaturesForProjection(data: GeoJsonObject, projection: PortalProjection) {
  const format = new GeoJSON();
  const features = format.readFeatures(data, {
    dataProjection: 'EPSG:4326',
    featureProjection: 'EPSG:4326',
  });

  return features
    .filter(feature => {
      const extent = feature.getGeometry()?.getExtent();
      if (!extent) return false;
      if (projection === 'EPSG:3995') return extent[3] >= 15;
      if (projection === 'EPSG:3031') return extent[1] <= -15;
      return true;
    })
    .map(feature => {
      feature.getGeometry()?.transform('EPSG:4326', projection);
      return feature;
    });
}

export function PortalMap({
  records,
  onSelect,
  onBox,
}: {
  records: WigosRecord[];
  onSelect: (record: WigosRecord | null) => void;
  onBox: (bbox4326: number[]) => void;
}) {
  const target = useRef<HTMLDivElement>(null);
  const tooltip = useRef<HTMLDivElement>(null);
  const mapRef = useRef<OlMap | null>(null);
  const [hovered, setHovered] = useState<WigosRecord | null>(null);
  const [projection, setProjection] = useState<PortalProjection>('ESRI:54009');
  const [boxMode, setBoxMode] = useState(false);
  const [basemapData, setBasemapData] = useState<GeoJsonObject | null>(null);
  const [basemapError, setBasemapError] = useState<string | null>(null);
  const boxRef = useRef<DragBox | null>(null);
  const recordIndex = useRef(new globalThis.Map<string, WigosRecord>());

  useEffect(() => {
    let cancelled = false;

    fetch('/basemap/ne_110m_admin_0_countries.geojson')
      .then(response => {
        if (!response.ok) throw new Error(`Basemap request failed: HTTP ${response.status}`);
        return response.json() as Promise<GeoJsonObject>;
      })
      .then(data => {
        if (!cancelled) setBasemapData(data);
      })
      .catch(error => {
        if (!cancelled) setBasemapError(error instanceof Error ? error.message : String(error));
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!target.current || !tooltip.current) return;

    const d = defaultView('ESRI:54009');
    const overlay = new Overlay({
      element: tooltip.current,
      offset: [10, -10],
      positioning: 'bottom-left',
      stopEvent: false,
    });

    const map = new OlMap({
      target: target.current,
      layers: [basemapLayer, graticuleLayer, frameLayer, stationLayer],
      overlays: [overlay],
      view: new View({
        projection: 'ESRI:54009',
        center: d.center,
        zoom: d.zoom,
      }),
    });

    map.on('pointermove', event => {
      if (event.dragging) return;
      const feature = map.forEachFeatureAtPixel(
        event.pixel,
        candidate => candidate,
        { layerFilter: candidate => candidate === stationLayer },
      );
      const id = feature?.getId();
      const record = id == null
        ? null
        : recordIndex.current.get(String(id)) || null;

      setHovered(record);
      overlay.setPosition(record ? event.coordinate : undefined);
      map.getTargetElement().style.cursor = record ? 'pointer' : '';
    });

    map.on('singleclick', event => {
      const feature = map.forEachFeatureAtPixel(
        event.pixel,
        candidate => candidate,
        { layerFilter: candidate => candidate === stationLayer },
      );
      const id = feature?.getId();
      onSelect(
        id == null
          ? null
          : recordIndex.current.get(String(id)) || null,
      );
    });

    mapRef.current = map;

    return () => {
      mapRef.current = null;
      map.setTarget(undefined);
    };
  }, [onSelect]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const d = defaultView(projection);
    const view = new View({
      projection,
      center: d.center,
      zoom: d.zoom,
    });
    map.setView(view);

    frameSource.clear();
    const frame = projectionFrame(projection);
    frameSource.addFeature(frame);
    const extent = frame.getGeometry()?.getExtent();
    const size = map.getSize();
    if (extent && size) {
      view.fit(extent, {
        size,
        padding: [34, 34, 34, 34],
        duration: 0,
      });
    }
  }, [projection]);

  useEffect(() => {
    basemapSource.clear();
    if (!basemapData) return;
    basemapSource.addFeatures(basemapFeaturesForProjection(basemapData, projection));
  }, [basemapData, projection]);

  useEffect(() => {
    const format = new GeoJSON();

    stationSource.clear();
    recordIndex.current = new globalThis.Map(
      records.map(record => [String(record.id), record]),
    );

    stationSource.addFeatures(
      format.readFeatures(
        { type: 'FeatureCollection', features: records },
        {
          dataProjection: 'EPSG:4326',
          featureProjection: projection,
        },
      ),
    );
  }, [records, projection]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (boxRef.current) {
      map.removeInteraction(boxRef.current);
      boxRef.current = null;
    }

    if (!boxMode) return;

    const box = new DragBox({ condition: () => true });

    box.on('boxend', () => {
      const extent = box.getGeometry().getExtent();
      onBox(transformExtent(extent, projection, 'EPSG:4326'));
      setBoxMode(false);
    });

    boxRef.current = box;
    map.addInteraction(box);

    return () => {
      map.removeInteraction(box);
      if (boxRef.current === box) boxRef.current = null;
    };
  }, [boxMode, onBox, projection]);

  return (
    <section className="map-wrap">
      <div className="map-toolbar">
        {(Object.keys(projectionLabels) as PortalProjection[]).map(code => (
          <button
            key={code}
            className={projection === code ? 'active' : ''}
            onClick={() => setProjection(code)}
          >
            {projectionLabels[code]}
          </button>
        ))}
        <button
          className={boxMode ? 'active' : ''}
          onClick={() => setBoxMode(value => !value)}
        >
          Box select
        </button>
      </div>

      <div ref={target} className="map" />

      <div className="map-attribution">
        Made with Natural Earth
        {basemapError && <span className="map-basemap-error"> · basemap unavailable</span>}
      </div>

      <div
        ref={tooltip}
        className={`map-tooltip ${hovered ? '' : 'hidden'}`}
      >
        {hovered && (
          <>
            <strong>{hovered.properties.title || hovered.id}</strong>
            <span>{hovered.id}</span>
            <span>
              {[
                tail(hovered.properties.territory),
                tail(hovered.properties.facilityType),
              ].filter(Boolean).join(' · ')}
            </span>
            <span>
              {hovered.properties.currentObservationSeriesCount
                ?? hovered.properties.observationSeriesCount
                ?? '—'} current observation series
            </span>
          </>
        )}
      </div>
    </section>
  );
}
