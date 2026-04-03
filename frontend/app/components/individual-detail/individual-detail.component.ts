import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { GN2CommonModule } from '@geonature_common/GN2Common.module';
import { ActivatedRoute } from '@angular/router';
import { Observable, of } from 'rxjs';
import { catchError, distinctUntilChanged, map, shareReplay, startWith, switchMap, tap } from 'rxjs/operators';

import { Individual } from '../../models/individual';
import { IndividualComponent } from '../individual/individual.component';
import { IndividualService } from '../../services/individual.service';

@Component({
  standalone: true,
  templateUrl: 'individual-detail.component.html',
  styleUrls: ['./individual-detail.component.scss'],
  imports: [
    GN2CommonModule,
    CommonModule,
    IndividualComponent
  ],
})
export class IndividualDetailComponent implements OnInit {
  individual: Individual | null = null;
  routeIdSnapshot: number | null = null;
  routeIdParams$!: Observable<number | null>;
  individual$!: Observable<Individual | null>;
  statusSteps = ['route snapshot', 'route params$', 'backend individual$'];

  constructor(
    private _individualService: IndividualService,
    private _route: ActivatedRoute,
  ) {}

  ngOnInit() {
    this.routeIdSnapshot = this.parseId(this._route.snapshot.paramMap.get('id_individual'));
    console.log('routeIdSnapshot:', this.routeIdSnapshot);

    // pipe : pour traiter un enchainement de fonctions sur les observables
    this.routeIdParams$ = this._route.paramMap.pipe(
      map((params) => this.parseId(params.get('id_individual'))),
      distinctUntilChanged(),
      tap((id) => console.log('Emitted ID:', id)) // Log the emitted values
    );

    console.log('routeIdParams$', this.routeIdParams$);
    this.individual$ = this.routeIdParams$.pipe(
      switchMap((id) => {
        if (id === null) {
          return of(null);
        }

        return this._individualService.getIndividual(id).pipe(
          catchError(() => of(null))
        );
      }),
      tap((individual) => {
        console.log('Received individual:', individual);
        this.individual = individual[0];
      }),
      shareReplay(1)
    );
  }

  // ngOnInit() {
  //   this._route.paramMap.pipe(
  //     map((params) => this.parseId(params.get('id_individual'))),
  //     distinctUntilChanged(), // Only proceed if the ID has changed
  //     tap((id) => console.log('Emitted ID:', id)), // Log the emitted values
  //     switchMap((id) => { // SwitchMap : pour annuler la requete en cours si une nouvelle valeur arrive
  //       if (id === null) {
  //         return of(null);
  //       }
  //       console.log('Fetching individual with id:', id);
  //       return this._individualService.getIndividual(id).pipe(
  //         catchError(() => of(null))
  //       );
  //     })
  //   )
  // }

  private parseId(rawId: string | null): number | null {
    if (rawId === null) {
      return null;
    }
    const parsed = Number(rawId);
    return Number.isNaN(parsed) ? null : parsed;
  }
}
