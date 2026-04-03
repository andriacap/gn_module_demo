import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from '@geonature/services/config.service';
import { ModuleService } from '@geonature/services/module.service';

import { Individual } from '../models/individual';
import { PaginatedResponse } from '../models/pagination';

@Injectable()
export class IndividualService {
  constructor(
    private _http: HttpClient,
    private _config: ConfigService,
    private _moduleService: ModuleService
  ) {}

  getIndividuals(page = 1, limit = 5): Observable<PaginatedResponse<Individual>> {
    let params = new HttpParams().set('page', String(page)).set('limit', String(limit));

    console.log('API endpoint:', `${this._config.API_ENDPOINT}/${this._moduleService.currentModule.module_url}/indivs`);
    return this._http.get<PaginatedResponse<Individual>>(
      `${this._config.API_ENDPOINT}/${this._moduleService.currentModule.module_url}/indiv`, { params }
    );
  }

  getIndividual(id_individual: number): Observable<Individual> {
    return this._http.get<Individual>(
      `${this._config.API_ENDPOINT}/${this._moduleService.currentModule.module_url}/indiv/${id_individual}`
    );
  }

  createIndividual(individual: Omit<Individual, 'id_individual'>): Observable<Individual> {
    return this._http.post<Individual>(
      `${this._config.API_ENDPOINT}/${this._moduleService.currentModule.module_url}/indiv`,
      individual
    );
  }
}
