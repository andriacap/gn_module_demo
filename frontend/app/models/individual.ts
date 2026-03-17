import { TaxrefLite } from './taxref';

export interface GeoJsonGeometry {
  type: 'Point' | 'LineString' | 'Polygon';
  coordinates: unknown;
}

export interface Individual {
  id_individual: number;
  name_individual: string;
  cd_nom: number | null;
  observer?: number | null;
  observer_full_name?: string | null;
  taxref?: TaxrefLite | null;
  geom?: GeoJsonGeometry | null;
  additional_data?: {
    age?: number | null;
    sex?: string | null;
    notes?: string | null;
    [key: string]: unknown;
  } | null;
}

export interface IndividualPayload {
  name_individual: string;
  cd_nom: number | null;
  observer?: number | null;
  geom?: GeoJsonGeometry | null;
  additional_data?: Record<string, unknown>;
}

export interface IndividualFilters {
  name?: string | null;
  taxref?: string | null;
  observer?: string | null;
  date_from?: string | null;
  date_to?: string | null;
}

export interface IndividualMapFeature {
  type: 'Feature';
  id: number;
  geometry: GeoJsonGeometry | null;
  properties: Individual;
}

export interface IndividualMapFeatureCollection {
  type: 'FeatureCollection';
  features: IndividualMapFeature[];
}
