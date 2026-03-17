import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from '@geonature/services/config.service';
import { ModuleService } from '@geonature/services/module.service';

import { DEMO_ENDPOINTS } from '../constants/demo-endpoints';
import { Demo } from '../models/demo';
import { DemoStats } from '../models/demo-stats';
import {
  Individual,
  IndividualFilters,
  IndividualMapFeatureCollection,
  IndividualPayload,
} from '../models/individual';
import { PaginatedResponse } from '../models/pagination';
import { TaxrefLite } from '../models/taxref';

@Injectable()
export class DemoService {
  constructor(
    private _http: HttpClient,
    private _config: ConfigService,
    private _moduleService: ModuleService
  ) {}

  private get baseUrl(): string {
    return `${this._config.API_ENDPOINT}/${this._moduleService.currentModule.module_url}`;
  }

  private buildUrl(path: string): string {
    if (!path) {
      return `${this.baseUrl}/`;
    }
    return `${this.baseUrl}/${path}`;
  }

  getDemos(): Observable<Demo[]> {
    return this._http.get<Demo[]>(this.buildUrl(DEMO_ENDPOINTS.demos));
  }

  getDemo(id_demo: number): Observable<Demo> {
    return this._http.get<Demo>(this.buildUrl(String(id_demo)));
  }

  getIndividuals(
    page = 1,
    limit = 10,
    filters: IndividualFilters = {}
  ): Observable<PaginatedResponse<Individual>> {
    let params = new HttpParams().set('page', String(page)).set('limit', String(limit));
    params = this.appendIndividualFilters(params, filters);
    return this._http.get<PaginatedResponse<Individual>>(this.buildUrl(DEMO_ENDPOINTS.individuals), {
      params,
    });
  }

  getIndividualsGeojson(filters: IndividualFilters = {}): Observable<IndividualMapFeatureCollection> {
    const params = this.appendIndividualFilters(new HttpParams(), filters);
    return this._http.get<IndividualMapFeatureCollection>(
      this.buildUrl(DEMO_ENDPOINTS.individualsGeojson),
      { params }
    );
  }

  createIndividual(payload: IndividualPayload): Observable<Individual> {
    return this._http.post<Individual>(this.buildUrl(DEMO_ENDPOINTS.individuals), payload);
  }

  validateIndividual(payload: Partial<IndividualPayload>): Observable<{ valid: boolean; errors?: unknown }> {
    return this._http.post<{ valid: boolean; errors?: unknown }>(
      this.buildUrl(DEMO_ENDPOINTS.individualsValidate),
      payload
    );
  }

  updateIndividual(id_individual: number, payload: Partial<IndividualPayload>): Observable<Individual> {
    return this._http.put<Individual>(
      this.buildUrl(`${DEMO_ENDPOINTS.individuals}/${id_individual}`),
      payload
    );
  }

  deleteIndividual(id_individual: number): Observable<{ status: string; id_individual: number }> {
    return this._http.delete<{ status: string; id_individual: number }>(
      this.buildUrl(`${DEMO_ENDPOINTS.individuals}/${id_individual}`)
    );
  }

  getDemoStats(a: number, b: number): Observable<DemoStats> {
    const params = new HttpParams().set('a', a).set('b', b);
    return this._http.get<DemoStats>(this.buildUrl(DEMO_ENDPOINTS.demoStats), { params });
  }

  searchTaxref(query: string, limit = 10): Observable<TaxrefLite[]> {
    const params = new HttpParams().set('q', query).set('limit', limit);
    return this._http.get<TaxrefLite[]>(this.buildUrl(DEMO_ENDPOINTS.taxrefAutocomplete), {
      params,
    });
  }

  getMockStrategies(strategies: string[]): Observable<{ strategies: Array<{ strategy: string; count: number }> }> {
    let params = new HttpParams();
    strategies.forEach((strategy) => {
      params = params.append('strategy', strategy);
    });
    return this._http.get<{ strategies: Array<{ strategy: string; count: number }> }>(
      this.buildUrl(DEMO_ENDPOINTS.mockStrategies),
      { params }
    );
  }

  private appendIndividualFilters(params: HttpParams, filters: IndividualFilters): HttpParams {
    const normalized: Record<string, string> = {};
    const name = (filters.name ?? '').trim();
    const taxref = (filters.taxref ?? '').trim();
    const observer = (filters.observer ?? '').trim();
    const dateFrom = (filters.date_from ?? '').trim();
    const dateTo = (filters.date_to ?? '').trim();

    if (name) {
      normalized.name = name;
    }
    if (taxref) {
      normalized.taxref = taxref;
    }
    if (observer) {
      normalized.observer = observer;
    }
    if (dateFrom) {
      normalized.date_from = dateFrom;
    }
    if (dateTo) {
      normalized.date_to = dateTo;
    }

    Object.entries(normalized).forEach(([key, value]) => {
      params = params.set(key, value);
    });
    return params;
  }
}
