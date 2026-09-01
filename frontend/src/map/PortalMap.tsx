import { useEffect, useRef, useState } from 'react';
import Feature from 'ol/Feature';
import OlMap from 'ol/Map';
import Overlay from 'ol/Overlay';
import View from 'ol/View';
import GeoJSON from 'ol/format/GeoJSON';
import Polygon from 'ol/geom/Polygon';
import DragBox from 'ol/interaction/DragBox';
import Graticule from 'ol/layer/Graticule';
import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import { transform, transformExtent } from 'ol/proj';
import OSM from 'ol/source/OSM';
import VectorSource from 'ol/source/Vector';
import { Circle as CircleStyle, Fill, Stroke, Style } from 'ol/style';
import type { WigosRecord } from '../api/records';
import { defaultView, projectionLabels, type PortalProjection } from './projections';
import './basemap.css';

type GeoJsonObject = Record<string, unknown>;
type OverviewProjection = Exclude<PortalProjection, 'EPSG:3857'>;

const DETAIL_MAX_LONGITUDE_SPAN = 60;
const DETAIL_MAX_LATITUDE_SPAN = 45;
const WEB_MERCATOR_MAX_LATITUDE = 85.05112878;

function geographicViewport(map: OlMap): number[] | null {
  const size = map.getSize();
  if (!size) return null;

  try {
    const extent = map.getView().calculateExtent(size);
    const geographic = transformExtent(
      extent,
      map.getView().getProjection().getCode(),
      'EPSG:4326',
      8,
    );
    return geographic.every(Number.isFinite) ? geographic : null;
  } catch {
    return null;
  }
}

function detailedMapMakesSense(map: OlMap): boolean {
  const extent = geographicViewport(map);
  if (!extent) return false;

  const [west, south, east, north] = extent;
  const longitudeSpan = Math.abs(east - west);
  const latitudeSpan = Math.abs(north - south);
  const centreLatitude = (south + north) / 2;

  return (
    longitudeSpan <= DETAIL_MAX_LONGITUDE_SPAN &&
    latitudeSpan <= DETAIL_MAX_LATITUDE_SPAN &&
    Math.abs(centreLatitude) < WEB_MERCATOR_MAX_LATITUDE
  );
}

function tail(value?: string) {
  if (!value) return '';
  const parts = value.split('/');
  return parts[parts.length - 1] || value;
}

function projectionFrame(code: OverviewProjection) {
  const geographicRing: number[][] = [];

  if (code === 'ESRI:54009') {
    for (let lat = -89.9; lat <= 89.9; lat += 2) geographicRing.push([180, lat]);
    for (let lat = 89.9; lat >= -89.9; lat -= 2) geographicRing.push([-180, lat]);
  } else {
    const latitude = code === 'EPSG:3995' ? 20 : -20;
    for (let lon = -180; lon <= 180; lon += 3) geographicRing.push([lon, latitude]);
  }

  geographicRing.push(geographicRing[0]);
  const projected = geographicRing.map(coordinate =>
    transform(coordinate, 'EPSG:4326', code),
  );
  return new Feature(new Polygon([projected]));
}

function basemapFeaturesForProjection(
  data: GeoJsonObject,
  projection: OverviewProjection,
) {
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

function safeGeographicCenter(
  center: number[] | undefined,
  sourceProjection: string,
): [number, number] | null {
  if (!center) return null;
  try {
    const candidate = transform(center, sourceProjection, 'EPSG:4326');
    if (!candidate.every(Number.isFinite)) return null;
    return [candidate[0], candidate[1]];
  } catch {
    return null;
  }
}

function centerForProjection(
  geographicCenter: [number, number] | null,
  projection: PortalProjection,
) {
  const fallback = defaultView(projection).center;
  if (!geographicCenter) return fallback;

  let [lon, lat] = geographicCenter;

  if (projection === 'EPSG:3857') {
    lat = Math.max(-85.05112878, Math.min(85.05112878, lat));
  }

  try {
    const candidate = transform([lon, lat], 'EPSG:4326', projection);
    return candidate.every(Number.isFinite) ? candidate : fallback;
  } catch {
    return fallback;
  }
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
  const mapRef = useRef<OlMap | null>(null);
  const lastGeographicCenter = useRef<[number, number] | null>(null);
  const lastLocalZoom = useRef<number>(4);
  const overviewProjection = useRef<OverviewProjection>('ESRI:54009');
  const overviewExtent4326 = useRef<number[] | null>(null);
  const pendingFitExtent4326 = useRef<number[] | null>(null);

  const [projection, setProjection] = useState<PortalProjection>('ESRI:54009');
  const [canUseDetailedMap, setCanUseDetailedMap] = useState(false);
  const [boxMode, setBoxMode] = useState(false);
  const [basemapData, setBasemapData] = useState<GeoJsonObject | null>(null);
  const [basemapError, setBasemapError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetch('/basemap/ne_110m_admin_0_countries.geojson')
      .then(response => {
        if (!response.ok) {
          throw new Error(`Basemap request failed: HTTP ${response.status}`);
        }
        return response.json() as Promise<GeoJsonObject>;
      })
      .then(data => {
        if (!cancelled) setBasemapData(data);
      })
      .catch(error => {
        if (!cancelled) {
          setBasemapError(error instanceof Error ? error.message : String(error));
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  /*
   * Projection changes deliberately recreate the OpenLayers map rather than
   * mutating a live map between Mollweide / polar stereographic / Web Mercator.
   *
   * This is slightly heavier than map.setView(), but much safer: all layers,
   * sources, geometries, graticule state and interactions are created in the
   * coordinate system of the active View and discarded together on cleanup.
   */
  useEffect(() => {
    if (!target.current) return;

    const local = projection === 'EPSG:3857';
    const d = defaultView(projection);

    const stationSource = new VectorSource({ wrapX: false });
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

    const layers = [];

    if (local) {
      layers.push(
        new TileLayer({
          source: new OSM({
            crossOrigin: 'anonymous',
          }),
        }),
      );
    } else {
      const basemapSource = new VectorSource({ wrapX: false });

      if (basemapData) {
        basemapSource.addFeatures(
          basemapFeaturesForProjection(
            basemapData,
            projection as OverviewProjection,
          ),
        );
      }

      layers.push(
        new VectorLayer({
          source: basemapSource,
          style: new Style({
            fill: new Fill({ color: 'rgba(239, 241, 236, 1)' }),
            stroke: new Stroke({
              color: 'rgba(113, 126, 126, 0.72)',
              width: 0.7,
            }),
          }),
        }),
      );

      layers.push(
        new Graticule({
          strokeStyle: new Stroke({
            color: 'rgba(94, 118, 125, 0.32)',
            width: 0.65,
          }),
          showLabels: false,
          wrapX: false,
          targetSize: 150,
        }),
      );

      const frameSource = new VectorSource({ wrapX: false });
      const frame = projectionFrame(
        projection as OverviewProjection,
      );
      frameSource.addFeature(frame);

      layers.push(
        new VectorLayer({
          source: frameSource,
          style: new Style({
            fill: new Fill({ color: 'rgba(0, 0, 0, 0)' }),
            stroke: new Stroke({
              color: 'rgba(82, 99, 104, 0.9)',
              width: 1.15,
            }),
          }),
        }),
      );
    }

    layers.push(stationLayer);

    // IMPORTANT: the tooltip DOM node is owned by OpenLayers, not React.
    // Passing a React-rendered element to Overlay causes OpenLayers to move
    // that node into its overlay container. React still believes the node is
    // in its original JSX position and can later crash with:
    //   NotFoundError: Failed to execute 'insertBefore' on 'Node'
    const tooltipElement = document.createElement('div');
    tooltipElement.className = 'map-tooltip hidden';

    const overlay = new Overlay({
      element: tooltipElement,
      offset: [10, -10],
      positioning: 'bottom-left',
      stopEvent: false,
    });

    const center = centerForProjection(lastGeographicCenter.current, projection);

    const view = new View({
      projection,
      center,
      zoom: local ? lastLocalZoom.current : d.zoom,
      maxZoom: local ? 20 : 10,
    });

    const map = new OlMap({
      target: target.current,
      layers,
      overlays: [overlay],
      view,
    });

    mapRef.current = map;

    const recordIndex = new globalThis.Map(
      records.map(record => [String(record.id), record]),
    );

    const format = new GeoJSON();
    stationSource.addFeatures(
      format.readFeatures(
        { type: 'FeatureCollection', features: records },
        {
          dataProjection: 'EPSG:4326',
          featureProjection: projection,
        },
      ),
    );

    const fitExtent4326 = pendingFitExtent4326.current;
    pendingFitExtent4326.current = null;

    if (fitExtent4326 && map.getSize()) {
      try {
        view.fit(
          transformExtent(
            fitExtent4326,
            'EPSG:4326',
            projection,
            8,
          ),
          {
            size: map.getSize(),
            padding: [24, 24, 24, 24],
            duration: 0,
          },
        );
      } catch {
        view.setCenter(center);
        view.setZoom(local ? lastLocalZoom.current : d.zoom);
      }
    } else if (!local) {
      /*
       * Use the known projection defaults for a newly selected overview
       * projection. This avoids station distribution influencing the view.
       */
      view.setCenter(d.center);
      view.setZoom(d.zoom);
    }

    map.on('pointermove', event => {
      if (event.dragging) return;

      const feature = map.forEachFeatureAtPixel(
        event.pixel,
        candidate => candidate,
        { layerFilter: candidate => candidate === stationLayer },
      );
      const id = feature?.getId();
      const record =
        id == null ? null : recordIndex.get(String(id)) || null;

      if (record) {
        tooltipElement.replaceChildren();

        const title = document.createElement('strong');
        title.textContent = record.properties.title || String(record.id);
        tooltipElement.appendChild(title);

        const idLine = document.createElement('span');
        idLine.textContent = String(record.id);
        tooltipElement.appendChild(idLine);

        const metaLine = document.createElement('span');
        metaLine.textContent = [
          tail(record.properties.territory),
          tail(record.properties.facilityType),
        ]
          .filter(Boolean)
          .join(' · ');
        tooltipElement.appendChild(metaLine);

        const seriesLine = document.createElement('span');
        const seriesCount =
          record.properties.currentObservationSeriesCount ??
          record.properties.observationSeriesCount ??
          '—';
        seriesLine.textContent = `${seriesCount} current observation series`;
        tooltipElement.appendChild(seriesLine);

        tooltipElement.classList.remove('hidden');
        overlay.setPosition(event.coordinate);
      } else {
        tooltipElement.classList.add('hidden');
        overlay.setPosition(undefined);
      }

      map.getTargetElement().style.cursor = record ? 'pointer' : '';
    });

    map.on('singleclick', event => {
      const feature = map.forEachFeatureAtPixel(
        event.pixel,
        candidate => candidate,
        { layerFilter: candidate => candidate === stationLayer },
      );
      const id = feature?.getId();
      onSelect(id == null ? null : recordIndex.get(String(id)) || null);
    });

    const updateMapState = () => {
      const currentView = map.getView();
      lastGeographicCenter.current = safeGeographicCenter(
        currentView.getCenter(),
        currentView.getProjection().getCode(),
      );

      if (currentView.getProjection().getCode() === 'EPSG:3857') {
        lastLocalZoom.current = Math.max(
          2,
          Math.min(currentView.getZoom() ?? 4, 20),
        );
        setCanUseDetailedMap(false);
      } else {
        const extent4326 = geographicViewport(map);
        if (extent4326) overviewExtent4326.current = extent4326;
        setCanUseDetailedMap(detailedMapMakesSense(map));
      }
    };

    map.on('moveend', updateMapState);

    // Initial availability once the map has a size and the restored/default
    // extent has been applied.
    requestAnimationFrame(updateMapState);

    let box: DragBox | null = null;
    if (boxMode) {
      box = new DragBox({ condition: () => true });

      box.on('boxend', () => {
        const extent = box!.getGeometry().getExtent();
        onBox(transformExtent(extent, projection, 'EPSG:4326'));
        setBoxMode(false);
      });

      map.addInteraction(box);
    }

    return () => {
      const currentView = map.getView();
      lastGeographicCenter.current = safeGeographicCenter(
        currentView.getCenter(),
        currentView.getProjection().getCode(),
      );

      if (currentView.getProjection().getCode() === 'EPSG:3857') {
        lastLocalZoom.current = Math.max(
          2,
          Math.min(currentView.getZoom() ?? 4, 20),
        );
      } else {
        const extent4326 = geographicViewport(map);
        if (extent4326) overviewExtent4326.current = extent4326;
      }

      overlay.setPosition(undefined);
      tooltipElement.remove();
      mapRef.current = null;
      map.setTarget(undefined);
    };
  }, [projection, basemapData, records, boxMode, onSelect, onBox]);

  const local = projection === 'EPSG:3857';

  const selectOverviewProjection = (code: OverviewProjection) => {
    overviewProjection.current = code;
    overviewExtent4326.current = null;
    pendingFitExtent4326.current = null;
    setProjection(code);
  };

  const enterDetailedMap = () => {
    const map = mapRef.current;
    if (!map || projection === 'EPSG:3857') return;

    const extent4326 = geographicViewport(map);
    if (!extent4326 || !detailedMapMakesSense(map)) return;

    overviewProjection.current = projection as OverviewProjection;
    overviewExtent4326.current = extent4326;
    pendingFitExtent4326.current = extent4326;
    setProjection('EPSG:3857');
  };

  const returnToOverview = () => {
    pendingFitExtent4326.current = overviewExtent4326.current;
    setProjection(overviewProjection.current);
  };

  return (
    <section className="map-wrap">
      <div className="map-toolbar">
        {!local && (
          <>
            {(
              ['ESRI:54009', 'EPSG:3995', 'EPSG:3031'] as OverviewProjection[]
            ).map(code => (
              <button
                key={code}
                className={projection === code ? 'active' : ''}
                onClick={() => selectOverviewProjection(code)}
              >
                {projectionLabels[code]}
              </button>
            ))}

            {canUseDetailedMap && (
              <button
                className="map-detail-button"
                onClick={enterDetailedMap}
                title="Switch to a detailed OpenStreetMap view of the current area"
              >
                Detailed map
              </button>
            )}
          </>
        )}

        {local && (
          <button
            className="map-detail-button active"
            onClick={returnToOverview}
            title="Return to the previous overview projection and extent"
          >
            Back to overview
          </button>
        )}

        <button
          className={boxMode ? 'active' : ''}
          onClick={() => setBoxMode(value => !value)}
        >
          Box select
        </button>
      </div>

      <div ref={target} className="map" />

      <div className="map-attribution">
        {local ? (
          <>© OpenStreetMap contributors</>
        ) : (
          <>Made with Natural Earth</>
        )}
        {!local && basemapError && (
          <span className="map-basemap-error">
            {' '}
            · basemap unavailable
          </span>
        )}
      </div>

      {local && (
        <div className="map-mode-note">
          Detailed map · OpenStreetMap / Web Mercator
        </div>
      )}

    </section>
  );
}
