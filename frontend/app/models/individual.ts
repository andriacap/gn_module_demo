import { TaxrefLite } from './taxref';

export interface GeoJsonGeometry {
  type: 'Point' | 'LineString' | 'Polygon';
  coordinates: unknown;
}

export interface Individual {
  id_individual: number;
  name_individual: string;
  cd_nom: number | null;
  taxref?: TaxrefLite | null;
  geom?: GeoJsonGeometry | null;
  additional_data?: {
    age?: number | null;
    sex?: string | null;
    notes?: string | null;
  } | null;
}

export interface IndividualPayload {
  name_individual: string;
  cd_nom: number | null;
  geom?: GeoJsonGeometry | null;
  additional_data?: Record<string, unknown>;
}
