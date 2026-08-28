import { useEffect, useRef, useState } from 'react';
import OlMap from 'ol/Map';
import View from 'ol/View';
import Overlay from 'ol/Overlay';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import GeoJSON from 'ol/format/GeoJSON';
import DragBox from 'ol/interaction/DragBox';
import { Circle as CircleStyle, Fill, Stroke, Style } from 'ol/style';
import { transformExtent } from 'ol/proj';
import type { WigosRecord } from '../api/records';
import { defaultView, projectionLabels, type PortalProjection } from './projections';

const source = new VectorSource();
const layer = new VectorLayer({
  source,
  style: new Style({
    image: new CircleStyle({
      radius: 4,
      fill: new Fill({ color: '#1d6f8a' }),
      stroke: new Stroke({ color: '#ffffff', width: 1 }),
    }),
  }),
});

function tail(value?: string) {
  if (!value) return '';
  const parts = value.split('/');
  return parts[parts.length - 1] || value;
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
  const overlayRef = useRef<Overlay | null>(null);
  const [hovered, setHovered] = useState<WigosRecord | null>(null);
  const [projection, setProjection] = useState<PortalProjection>('ESRI:54009');
  const [boxMode, setBoxMode] = useState(false);
  const boxRef = useRef<DragBox | null>(null);
  const recordIndex = useRef(new globalThis.Map<string, WigosRecord>());

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
      layers: [layer],
      overlays: [overlay],
      view: new View({
        projection: 'ESRI:54009',
        center: d.center,
        zoom: d.zoom,
      }),
    });

    overlayRef.current = overlay;

    map.on('pointermove', event => {
      if (event.dragging) return;
      const feature = map.forEachFeatureAtPixel(event.pixel, f => f);
      const id = feature?.getId();
      const record = id == null
        ? null
        : recordIndex.current.get(String(id)) || null;

      setHovered(record);
      overlay.setPosition(record ? event.coordinate : undefined);
      map.getTargetElement().style.cursor = record ? 'pointer' : '';
    });

    map.on('singleclick', event => {
      const feature = map.forEachFeatureAtPixel(event.pixel, f => f);
      const id = feature?.getId();
      onSelect(
        id == null
          ? null
          : recordIndex.current.get(String(id)) || null,
      );
    });

    mapRef.current = map;

    return () => {
      overlayRef.current = null;
      mapRef.current = null;
      map.setTarget(undefined);
    };
  }, [onSelect]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const d = defaultView(projection);
    map.setView(new View({
      projection,
      center: d.center,
      zoom: d.zoom,
    }));
  }, [projection]);

  useEffect(() => {
    const format = new GeoJSON();

    source.clear();
    recordIndex.current = new globalThis.Map(
      records.map(record => [String(record.id), record]),
    );

    source.addFeatures(
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
      if (boxRef.current === box) {
        boxRef.current = null;
      }
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
