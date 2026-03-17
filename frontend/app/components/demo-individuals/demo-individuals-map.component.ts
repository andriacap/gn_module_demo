import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  NgZone,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import * as L from 'leaflet';

import { GN2CommonModule } from '@geonature_common/GN2Common.module';
import { MapService } from '@geonature_common/map/map.service';

import { Individual, IndividualMapFeature, IndividualMapFeatureCollection } from '../../models/individual';

const EMPTY_FEATURE_COLLECTION: IndividualMapFeatureCollection = {
  type: 'FeatureCollection',
  features: [],
};

@Component({
  selector: 'pnx-demo-individuals-map',
  standalone: true,
  templateUrl: './demo-individuals-map.component.html',
  styleUrls: ['./demo-individuals-map.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, GN2CommonModule],
  providers: [MapService],
})
export class DemoIndividualsMapComponent implements OnChanges, OnDestroy {
  @Input() featureCollection: IndividualMapFeatureCollection | null = EMPTY_FEATURE_COLLECTION;
  @Input() selectedIndividualId: number | null = null;
  @Output() individualSelected = new EventEmitter<number>();

  readonly defaultStyle: L.PathOptions = {
    color: '#2d6a4f',
    weight: 2,
    fillColor: '#52b788',
    fillOpacity: 0.3,
  };

  readonly selectedStyle: L.PathOptions = {
    color: '#d62828',
    weight: 4,
    fillColor: '#f77f00',
    fillOpacity: 0.5,
  };

  geojsonData: IndividualMapFeatureCollection = EMPTY_FEATURE_COLLECTION;

  private _layerByIndividualId = new Map<number, L.Path>();
  private _selectedLayer: L.Path | null = null;

  constructor(
    private _mapService: MapService,
    private _ngZone: NgZone
  ) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes.featureCollection) {
      this.geojsonData = this.normalizeFeatureCollection(this.featureCollection);
      this._layerByIndividualId.clear();
      this._selectedLayer = null;
    }

    if (changes.selectedIndividualId) {
      if (this.selectedIndividualId === null) {
        this.clearSelectedLayer();
      } else {
        this.selectIndividualLayer(this.selectedIndividualId, false);
      }
    }
  }

  ngOnDestroy() {
    this._layerByIndividualId.clear();
    this._selectedLayer = null;
  }

  focusIndividual(individualId: number, centerOnFeature: boolean) {
    this.selectIndividualLayer(individualId, centerOnFeature);
  }

  onEachFeature(feature: GeoJSON.Feature, layer: L.Layer) {
    const individualId = this.extractIndividualId(feature as unknown as IndividualMapFeature);
    if (individualId === null) {
      return;
    }

    const pathLayer = layer as L.Path;
    if (typeof pathLayer.setStyle !== 'function') {
      return;
    }

    this._layerByIndividualId.set(individualId, pathLayer);
    this.setLayerStyle(pathLayer, false);

    if (pathLayer instanceof L.CircleMarker) {
      pathLayer.setRadius(6);
    }

    const name = (feature.properties as Individual | undefined)?.name_individual;
    const label = name ? `${name} (#${individualId})` : `Individu #${individualId}`;
    pathLayer.bindTooltip(label, { sticky: true });

    pathLayer.on('click', () => {
      this._ngZone.run(() => {
        this.selectIndividualLayer(individualId, false);
        this.individualSelected.emit(individualId);
      });
    });

    if (this.selectedIndividualId === individualId) {
      this.selectIndividualLayer(individualId, false);
    }
  }

  private selectIndividualLayer(individualId: number, centerOnFeature: boolean) {
    const nextLayer = this._layerByIndividualId.get(individualId) ?? null;

    if (this._selectedLayer && this._selectedLayer !== nextLayer) {
      this.setLayerStyle(this._selectedLayer, false);
    }

    this._selectedLayer = nextLayer;
    if (!nextLayer) {
      return;
    }

    this.setLayerStyle(nextLayer, true);
    const frontLayer = nextLayer as L.Path & { bringToFront?: () => L.Path };
    if (typeof frontLayer.bringToFront === 'function') {
      frontLayer.bringToFront();
    }

    if (centerOnFeature) {
      this.centerMapOnLayer(nextLayer);
    }
  }

  private clearSelectedLayer() {
    if (!this._selectedLayer) {
      return;
    }
    this.setLayerStyle(this._selectedLayer, false);
    this._selectedLayer = null;
  }

  private centerMapOnLayer(layer: L.Layer) {
    const map = this._mapService.getMap();
    if (!map) {
      return;
    }

    if (layer instanceof L.Marker || layer instanceof L.CircleMarker || layer instanceof L.Circle) {
      const currentZoom = map.getZoom();
      const targetZoom = currentZoom < 14 ? 14 : currentZoom;
      map.setView(layer.getLatLng(), targetZoom);
      return;
    }

    const boundsLayer = layer as L.Layer & { getBounds?: () => L.LatLngBounds };
    if (typeof boundsLayer.getBounds === 'function') {
      const bounds = boundsLayer.getBounds();
      if (bounds?.isValid()) {
        map.fitBounds(bounds, { maxZoom: 15, padding: [24, 24] });
      }
    }
  }

  private setLayerStyle(layer: L.Path, selected: boolean) {
    const feature = (layer as L.Path & { feature?: GeoJSON.Feature }).feature;
    layer.setStyle(this.getLayerStyle(feature, selected));

    if (layer instanceof L.CircleMarker) {
      layer.setRadius(selected ? 8 : 6);
    }
  }

  private getLayerStyle(feature: GeoJSON.Feature | undefined, selected: boolean): L.PathOptions {
    const style = selected ? this.selectedStyle : this.defaultStyle;
    const geometryType = feature?.geometry?.type;
    if (geometryType === 'LineString' || geometryType === 'MultiLineString') {
      return {
        ...style,
        fill: false,
      };
    }
    return style;
  }

  private normalizeFeatureCollection(
    featureCollection: IndividualMapFeatureCollection | null | undefined
  ): IndividualMapFeatureCollection {
    if (
      !featureCollection ||
      featureCollection.type !== 'FeatureCollection' ||
      !Array.isArray(featureCollection.features)
    ) {
      return EMPTY_FEATURE_COLLECTION;
    }

    return {
      type: 'FeatureCollection',
      features: featureCollection.features,
    };
  }

  private extractIndividualId(feature: Partial<IndividualMapFeature> | null | undefined): number | null {
    const idFromProperties = Number(feature?.properties?.id_individual);
    if (Number.isInteger(idFromProperties)) {
      return idFromProperties;
    }

    const idFromFeature = Number(feature?.id);
    if (Number.isInteger(idFromFeature)) {
      return idFromFeature;
    }

    return null;
  }
}
