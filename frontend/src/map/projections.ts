import proj4 from 'proj4';
import { register } from 'ol/proj/proj4';
import { get as getProjection, transform } from 'ol/proj';

export type PortalProjection = 'ESRI:54009' | 'EPSG:3995' | 'EPSG:3031';

proj4.defs('ESRI:54009', '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs +type=crs');
proj4.defs('EPSG:3995', '+proj=stere +lat_0=90 +lat_ts=71 +lon_0=0 +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs +type=crs');
proj4.defs('EPSG:3031', '+proj=stere +lat_0=-90 +lat_ts=-71 +lon_0=0 +k=1 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs +type=crs');
register(proj4);

const moll = getProjection('ESRI:54009');
if (moll) {
  moll.setExtent([-18040095.7, -9020047.8, 18040095.7, 9020047.8]);
  moll.setWorldExtent([-180, -90, 180, 90]);
}

const arctic = getProjection('EPSG:3995');
if (arctic) {
  arctic.setExtent([-5200000, -5200000, 5200000, 5200000]);
  arctic.setWorldExtent([-180, 15, 180, 90]);
}

const antarctic = getProjection('EPSG:3031');
if (antarctic) {
  antarctic.setExtent([-5200000, -5200000, 5200000, 5200000]);
  antarctic.setWorldExtent([-180, -90, 180, -15]);
}

export const projectionLabels: Record<PortalProjection, string> = {
  'ESRI:54009': 'Global',
  'EPSG:3995': 'Arctic',
  'EPSG:3031': 'Antarctic',
};

export function defaultView(code: PortalProjection) {
  if (code === 'EPSG:3995') return { center: transform([0, 90], 'EPSG:4326', code), zoom: 2.2 };
  if (code === 'EPSG:3031') return { center: transform([0, -90], 'EPSG:4326', code), zoom: 2.2 };
  return { center: transform([0, 0], 'EPSG:4326', code), zoom: 1.7 };
}
