import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { GN2CommonModule } from '@geonature_common/GN2Common.module';
import { RouterModule } from '@angular/router';
import { BehaviorSubject,Observable } from 'rxjs';
import { switchMap, tap, shareReplay } from 'rxjs/operators';
import { Individual } from '../../models/individual';
import { PaginatedResponse } from '../../models/pagination';
import { IndividualComponent } from '../individual/individual.component';
import { IndividualService } from '../../services/individual.service';

@Component({
  standalone: true,
  templateUrl: 'individual-list.component.html',
  styleUrls: ['./individual-list.component.scss'],
  imports: [
    GN2CommonModule,
    CommonModule,
    RouterModule,
    IndividualComponent
  ],
})
export class IndividualListComponent implements OnInit {
  individuals$: Observable<PaginatedResponse<Individual>>;

  private _pagination$ = new BehaviorSubject<{ page: number; limit: number }>({
    page: 1,
    limit: 5,
  });

  columns = [
    { prop: 'name', name: 'Individu' },
    { prop: 'taxref.nom_vern', name: 'Taxon' },
    { prop: 'nomenclature_sex.label_fr', name: 'Sexe' },
  ];

  constructor(
    private _individualService: IndividualService,
  ) {}

  ngOnInit() {
    console.log('Fetching individuals...');
    
    this.individuals$ = this._pagination$.pipe(
      switchMap(({ page, limit }) => this._individualService.getIndividuals(page, limit)),
      shareReplay({ bufferSize: 1, refCount: true })
    );
  }

  onPage($event) {
    this._pagination$.next({
      page: Number($event.offset ?? 0) + 1,
      limit: Number($event.limit ?? this._pagination$.getValue().limit),
    });
    console.log('Next pagination state:', this._pagination$.getValue());
  }
}