import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnDestroy,
  OnInit,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { BehaviorSubject, Observable, Subject, combineLatest, of, timer } from 'rxjs';
import { catchError, map, shareReplay, switchMap, take, takeUntil, tap } from 'rxjs/operators';
import {
  AbstractControl,
  AsyncValidatorFn,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { GN2CommonModule } from '@geonature_common/GN2Common.module';
import { leafletDrawOption } from '@geonature_common/map/leaflet-draw.options';
import { MapService } from '@geonature_common/map/map.service';
import { ConfigService } from '@geonature/services/config.service';

import {
  GeoJsonGeometry,
  Individual,
  IndividualFilters,
  IndividualMapFeatureCollection,
} from '../../models/individual';
import { PaginatedResponse } from '../../models/pagination';
import { DemoService } from '../../services/demo.service';
import { TaxrefLite } from '../../models/taxref';
import { DemoIndividualsMapComponent } from './demo-individuals-map.component';

const EMPTY_FEATURE_COLLECTION: IndividualMapFeatureCollection = {
  type: 'FeatureCollection',
  features: [],
};

type IndividualsViewMode = 'list' | 'create' | 'edit';

function positiveIntegerValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const value = Number(control.value);
    if (!Number.isInteger(value) || value <= 0) {
      return { positiveInteger: true };
    }
    return null;
  };
}

const ADDITIONAL_DATA_ALLOWED_SEX = ['M', 'F', 'U'];
const GEOM_ALLOWED_TYPES = ['Point', 'LineString', 'Polygon'];

function geometryValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const value = control.value;
    if (value === null || value === undefined) {
      return null;
    }
    if (typeof value !== 'object') {
      return { geometry: ['La geometrie doit etre un objet GeoJSON.'] };
    }
    const geometry = value as Partial<GeoJsonGeometry>;
    if (!geometry.type || !GEOM_ALLOWED_TYPES.includes(geometry.type)) {
      return {
        geometry: [`Le type de geometrie doit etre parmi: ${GEOM_ALLOWED_TYPES.join(', ')}.`],
      };
    }
    if (geometry.coordinates === undefined || geometry.coordinates === null) {
      return { geometry: ['Les coordonnees de la geometrie sont requises.'] };
    }
    return null;
  };
}

function additionalDataSyncValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const value = (control.value ?? {}) as {
      age?: unknown;
      sex?: unknown;
      notes?: unknown;
    };
    const age = value.age;
    const sexRaw = value.sex;
    const sex = typeof sexRaw === 'string' ? sexRaw.trim() : sexRaw;
    const notes = typeof value.notes === 'string' ? value.notes.trim() : value.notes;
    const hasAge = age !== null && age !== undefined && age !== '';
    const hasSex = sex !== null && sex !== undefined && sex !== '';
    const hasNotes = notes !== null && notes !== undefined && notes !== '';

    if (!hasAge && !hasSex && !hasNotes) {
      return null;
    }
    const errors: string[] = [];
    if (!hasAge || !hasSex) {
      errors.push('Les champs age et sex sont obligatoires ensemble.');
    }
    if (hasAge) {
      const parsedAge = Number(age);
      if (!Number.isInteger(parsedAge)) {
        errors.push("L'age doit etre un entier.");
      } else if (parsedAge < 0) {
        errors.push("L'age doit etre superieur ou egal a 0.");
      }
    }
    if (hasSex) {
      if (typeof sex !== 'string') {
        errors.push('Le champ sex doit etre une chaine.');
      } else if (!ADDITIONAL_DATA_ALLOWED_SEX.includes(sex)) {
        errors.push(`Sex doit etre parmi: ${ADDITIONAL_DATA_ALLOWED_SEX.join(', ')}.`);
      }
    }

    return errors.length ? { additionalData: errors } : null;
  };
}

function additionalDataAsyncValidator(demoService: DemoService): AsyncValidatorFn {
  return (control: AbstractControl) => {
    const value = (control.value ?? {}) as {
      age?: unknown;
      sex?: unknown;
      notes?: unknown;
    };
    const age = value.age;
    const sex = typeof value.sex === 'string' ? value.sex.trim() : value.sex;
    const notes = typeof value.notes === 'string' ? value.notes.trim() : value.notes;
    const hasAge = age !== null && age !== undefined && age !== '';
    const hasSex = sex !== null && sex !== undefined && sex !== '';
    const hasNotes = notes !== null && notes !== undefined && notes !== '';

    if (!hasAge && !hasSex && !hasNotes) {
      return of(null);
    }
    return timer(300).pipe(
      switchMap(() =>
        demoService.validateIndividual({
          additional_data: value,
        })
      ),
      map(() => null),
      catchError((err) => {
        const messages = err?.error?.errors?.additional_data;
        if (Array.isArray(messages) && messages.length) {
          return of({ additionalData: messages });
        }
        if (typeof messages === 'string') {
          return of({ additionalData: [messages] });
        }
        return of({ additionalData: ['Validation serveur: donnees additionnelles invalides.'] });
      })
    );
  };
}

@Component({
  standalone: true,
  templateUrl: './demo-individuals.component.html',
  styleUrls: ['./demo-individuals.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule, ReactiveFormsModule, GN2CommonModule, DemoIndividualsMapComponent],
})
export class DemoIndividualsComponent implements OnInit, OnDestroy {
  individuals$!: Observable<PaginatedResponse<Individual>>;
  viewMode: IndividualsViewMode = 'list';
  editIndividualId: number | null = null;
  saving = false;
  formLoading = false;
  errorMessage: string | null = null;
  formLoadErrorMessage: string | null = null;
  successMessage: string | null = null;
  editing: Individual | null = null;
  taxrefResults: TaxrefLite[] = [];
  taxrefLoading = false;
  selectedIndividualId: number | null = null;
  mapLoading = false;
  mapErrorMessage: string | null = null;

  readonly leafletDrawOptions = {
    ...leafletDrawOption,
    draw: {
      ...leafletDrawOption.draw,
      marker: true,
      polyline: true,
      polygon: {
        allowIntersection: false,
        drawError: {
          color: '#e1e100',
          message: 'Intersection forbidden !',
        },
      },
    },
    // edit: {
    //   ...leafletDrawOption.edit,
    //   remove: true,
    // },
  };

  private _pagination$ = new BehaviorSubject<{ page: number; limit: number }>({
    page: 1,
    limit: 10,
  });
  private _filters$ = new BehaviorSubject<IndividualFilters>({});
  private _refreshMap$ = new BehaviorSubject<number>(0);
  private _destroy$ = new Subject<void>();
  private _allIndividualIds: number[] = [];
  private _listPaginationSnapshot: PaginatedResponse<Individual> | null = null;
  private _individualsMapComponent: DemoIndividualsMapComponent | undefined;

  mapFeatureCollection: IndividualMapFeatureCollection = EMPTY_FEATURE_COLLECTION;

  @ViewChild(DemoIndividualsMapComponent)
  set individualsMapComponent(component: DemoIndividualsMapComponent | undefined) {
    this._individualsMapComponent = component;
    this.focusSelectedIndividualOnMap(false);
  }

  form = this._fb.group({
    name_individual: this._fb.control<string>('', [Validators.required, Validators.maxLength(80)]),
    cd_nom: this._fb.control<number | null>(null, [
      Validators.required,
      positiveIntegerValidator(),
    ]),
    observer: this._fb.control<number | null>(null),
    geom: this._fb.control<GeoJsonGeometry | null>(null, [geometryValidator()]),
    additional_data: this._fb.group(
      {
        age: [null],
        sex: [''],
        notes: [''],
      },
      {
        validators: [additionalDataSyncValidator()],
        asyncValidators: [additionalDataAsyncValidator(this._demoService)],
      }
    ),
  });

  filterForm = this._fb.group({
    name: this._fb.control<string>(''),
    taxref: this._fb.control<string>(''),
    observer: this._fb.control<number | null>(null),
    date_from: this._fb.control<string>(''),
    date_to: this._fb.control<string>(''),
  });

  constructor(
    private _demoService: DemoService,
    private _fb: FormBuilder,
    private _mapService: MapService,
    public config: ConfigService,
    private _cdr: ChangeDetectorRef,
    private _route: ActivatedRoute,
    private _router: Router
  ) {}

  ngOnInit() {
    this.resolveViewModeFromRoute();

    if (this.isListMode) {
      const selectedFromQuery = Number(this._route.snapshot.queryParamMap.get('selected'));
      if (Number.isInteger(selectedFromQuery) && selectedFromQuery > 0) {
        this.selectedIndividualId = selectedFromQuery;
      }
      this.initializeListAndMapStreams();
      return;
    }

    this.initializeFormMode();
  }

  ngOnDestroy() {
    this._destroy$.next();
    this._destroy$.complete();
  }

  get isListMode(): boolean {
    return this.viewMode === 'list';
  }

  get isFormMode(): boolean {
    return this.viewMode === 'create' || this.viewMode === 'edit';
  }

  get isEditMode(): boolean {
    return this.viewMode === 'edit';
  }

  get observerFilterListCode(): string {
    const configuredCode = String(this.config?.DEMO?.OBSERVERS_LIST_CODE ?? '').trim();
    return configuredCode || 'observateurs_individ';
  }

  private resolveViewModeFromRoute() {
    const routePath = this._route.snapshot.routeConfig?.path ?? 'individuals';

    if (routePath === 'individuals/new') {
      this.viewMode = 'create';
      return;
    }

    if (routePath === 'individuals/:id/edit') {
      this.viewMode = 'edit';
      return;
    }

    this.viewMode = 'list';
  }

  private initializeListAndMapStreams() {
    this.individuals$ = combineLatest([this._pagination$, this._filters$]).pipe(
      switchMap(([{ page, limit }, filters]) =>
        this._demoService.getIndividuals(page, limit, filters)
      ),
      tap((pagination) => {
        this._listPaginationSnapshot = pagination;
      }),
      shareReplay({ bufferSize: 1, refCount: true })
    );

    combineLatest([this._filters$, this._refreshMap$])
      .pipe(
        switchMap(([filters]) => {
          this.mapLoading = true;
          this.mapErrorMessage = null;
          this._cdr.markForCheck();

          return this._demoService.getIndividualsGeojson(filters).pipe(
            catchError(() => {
              this.mapErrorMessage = 'Erreur lors du chargement des geometries.';
              return of(EMPTY_FEATURE_COLLECTION);
            })
          );
        }),
        takeUntil(this._destroy$)
      )
      .subscribe((featureCollection) => {
        this.mapLoading = false;
        this.mapFeatureCollection = this.normalizeFeatureCollection(featureCollection);
        this._allIndividualIds = this.mapFeatureCollection.features
          .map((feature) => this.extractIndividualId(feature))
          .filter((id): id is number => id !== null);
        if (
          this.selectedIndividualId !== null &&
          !this._allIndividualIds.includes(this.selectedIndividualId)
        ) {
          this.selectedIndividualId = null;
        }
        if (this.selectedIndividualId !== null) {
          this.ensureSelectedIndividualPage(this.selectedIndividualId);
        }
        this.focusSelectedIndividualOnMap(false);
        this._cdr.markForCheck();
      });
  }

  private initializeFormMode() {
    this.formLoadErrorMessage = null;
    if (this.viewMode === 'create') {
      this.editIndividualId = null;
      this.editing = null;
      this.resetForm();
      return;
    }

    const id = Number(this._route.snapshot.paramMap.get('id'));
    if (!Number.isInteger(id) || id <= 0) {
      this.formLoadErrorMessage = "L'identifiant de l'individu est invalide.";
      return;
    }

    this.editIndividualId = id;
    const itemFromNavigationState = this.readIndividualFromNavigationState();
    if (itemFromNavigationState && itemFromNavigationState.id_individual === id) {
      this.startEdit(itemFromNavigationState);
      return;
    }

    this.loadIndividualForEdit(id);
  }

  private readIndividualFromNavigationState(): Individual | null {
    const navState =
      (
        this._router.getCurrentNavigation()?.extras?.state as
          | { individual?: Individual }
          | undefined
      )?.individual ??
      (window.history?.state as { individual?: Individual } | undefined)?.individual ??
      null;

    if (!navState || typeof navState !== 'object') {
      return null;
    }

    const id = Number(navState.id_individual);
    if (!Number.isInteger(id) || id <= 0) {
      return null;
    }

    return navState;
  }

  private loadIndividualForEdit(individualId: number) {
    this.formLoading = true;
    this.formLoadErrorMessage = null;
    const limit = this._pagination$.getValue().limit;

    this._demoService
      .getIndividualsGeojson({})
      .pipe(
        map((collection) => {
          const normalized = this.normalizeFeatureCollection(collection);
          const allIds = normalized.features
            .map((feature) => this.extractIndividualId(feature))
            .filter((id): id is number => id !== null);
          return allIds.indexOf(individualId);
        }),
        switchMap((index) => {
          if (index < 0) {
            return of<Individual | null>(null);
          }
          const page = Math.floor(index / limit) + 1;
          return this._demoService
            .getIndividuals(page, limit, {})
            .pipe(
              map(
                (pagination) =>
                  pagination.items.find((item) => item.id_individual === individualId) ?? null
              )
            );
        }),
        take(1)
      )
      .subscribe({
        next: (item) => {
          this.formLoading = false;
          if (!item) {
            this.formLoadErrorMessage = "Impossible de charger l'individu a modifier.";
            this._cdr.markForCheck();
            return;
          }
          this.startEdit(item);
          this._cdr.markForCheck();
        },
        error: () => {
          this.formLoading = false;
          this.formLoadErrorMessage = "Impossible de charger l'individu a modifier.";
          this._cdr.markForCheck();
        },
      });
  }

  searchTaxref(term: string) {
    const trimmed = (term || '').trim();
    if (trimmed.length < 2) {
      this.taxrefResults = [];
      return;
    }
    this.taxrefLoading = true;
    this._demoService.searchTaxref(trimmed).subscribe({
      next: (results) => {
        this.taxrefResults = results;
        this.taxrefLoading = false;
      },
      error: () => {
        this.taxrefResults = [];
        this.taxrefLoading = false;
      },
      complete: () => {
        this.taxrefLoading = false;
      },
    });
  }

  submit() {
    if (this.form.invalid || this.form.pending) {
      this.form.markAllAsTouched();
      return;
    }

    this.saving = true;
    this.errorMessage = null;
    this.successMessage = null;

    const additionalData = this.form.value.additional_data ?? {};
    const age = additionalData.age;
    const sex =
      typeof additionalData.sex === 'string' ? additionalData.sex.trim() : additionalData.sex;
    const notes =
      typeof additionalData.notes === 'string' ? additionalData.notes.trim() : additionalData.notes;
    const hasAge = age !== null && age !== undefined && age !== '';
    const hasSex = sex !== null && sex !== undefined && sex !== '';
    const hasNotes = notes !== null && notes !== undefined && notes !== '';

    const payloadAdditionalData =
      hasAge && hasSex
        ? {
            age: Number(age),
            sex,
            ...(hasNotes ? { notes } : {}),
          }
        : undefined;

    const observerRaw = this.form.value.observer;
    const observerParsed =
      observerRaw === null || observerRaw === undefined ? null : Number(observerRaw);
    const observerId =
      Number.isInteger(observerParsed) && Number(observerParsed) > 0
        ? Number(observerParsed)
        : null;

    const payload = {
      name_individual: this.form.value.name_individual ?? '',
      cd_nom: this.form.value.cd_nom ? Number(this.form.value.cd_nom) : null,
      observer: observerId,
      geom: this.form.value.geom ?? null,
      additional_data: payloadAdditionalData,
    };

    const wasEditing = this.isEditMode;
    if (wasEditing && !this.editIndividualId) {
      this.errorMessage = "Impossible de determiner l'individu a modifier.";
      this.saving = false;
      this._cdr.markForCheck();
      return;
    }

    const request$ = wasEditing
      ? this._demoService.updateIndividual(this.editIndividualId as number, payload)
      : this._demoService.createIndividual(payload);

    request$.pipe(take(1)).subscribe({
      next: (savedIndividual) => {
        this.selectedIndividualId = savedIndividual.id_individual;
        this.successMessage = wasEditing
          ? "L'individu a ete mis a jour."
          : "L'individu a ete ajoute.";
        this.saving = false;
        this.editing = null;
        this.resetForm();
        if (this.isFormMode) {
          this.navigateToList(savedIndividual.id_individual);
          return;
        }
        this.refreshPage();
        this.refreshMap();
        this._cdr.markForCheck();
      },
      error: (err) => {
        this.errorMessage = err?.message || 'Erreur lors de la sauvegarde.';
        this.saving = false;
        this._cdr.markForCheck();
      },
    });
  }

  startEdit(item: Individual) {
    this.editing = item;
    this.editIndividualId = item.id_individual;
    this.successMessage = null;
    this.errorMessage = null;
    this.form.patchValue({
      name_individual: item.name_individual,
      cd_nom: item.cd_nom,
      observer: item.observer ?? null,
      geom: item.geom ?? null,
      additional_data: {
        age: item.additional_data?.age ?? null,
        sex: item.additional_data?.sex ?? '',
        notes: item.additional_data?.notes ?? '',
      },
    });
    this.form.markAsPristine();
    this.taxrefResults = item.taxref ? [item.taxref] : [];
  }

  cancelEdit() {
    if (this.isFormMode) {
      this.navigateToList();
      return;
    }
    this.editing = null;
    this.editIndividualId = null;
    this.successMessage = null;
    this.errorMessage = null;
    this.resetForm();
  }

  goToCreatePage() {
    const routeParent = this._route.parent as ActivatedRoute;
    this._router.navigate(['individuals', 'new'], {
      relativeTo: routeParent,
    });
  }

  goToEditPage(item: Individual) {
    const routeParent = this._route.parent as ActivatedRoute;
    this._router.navigate(['individuals', item.id_individual, 'edit'], {
      relativeTo: routeParent,
      state: { individual: item },
    });
  }

  applyFilters() {
    const filters = this.getCurrentFilters();
    const pageState = this._pagination$.getValue();
    this._filters$.next(filters);
    this._pagination$.next({
      page: 1,
      limit: pageState.limit,
    });
    this.selectedIndividualId = null;
    this._cdr.markForCheck();
  }

  resetFilters() {
    this.filterForm.reset({
      name: '',
      taxref: '',
      observer: null,
      date_from: '',
      date_to: '',
    });
    this.applyFilters();
  }

  formatObserverDisplay(individual: Individual): string {
    const fullName = (individual.observer_full_name ?? '').trim();
    if (fullName) {
      return fullName;
    }

    const legacyObserverRaw = individual.additional_data?.observer;
    if (typeof legacyObserverRaw === 'string' && legacyObserverRaw.trim()) {
      return legacyObserverRaw.trim();
    }

    const observerId = Number(individual.observer);
    if (Number.isInteger(observerId) && observerId > 0) {
      return `#${observerId}`;
    }

    return '-';
  }

  onTableSelect(event: { selected?: Individual[] } | null) {
    const selected = event?.selected?.[0];
    if (!selected) {
      return;
    }
    this.selectIndividualFromList(selected);
  }

  onListPage(event: { offset: number; limit: number }) {
    const page = Number(event?.offset ?? 0) + 1;
    const limit = Number(event?.limit ?? this._pagination$.getValue().limit);
    this._pagination$.next({
      page: page > 0 ? page : 1,
      limit: limit > 0 ? limit : this._pagination$.getValue().limit,
    });
  }

  getSelectedRows(rows: Individual[]): Individual[] {
    if (this.selectedIndividualId === null) {
      return [];
    }
    return rows.filter((row) => row.id_individual === this.selectedIndividualId).slice(0, 1);
  }

  getDatatableRowClass = (row: Individual) => {
    return {
      'DemoIndividuals__row--selected': row?.id_individual === this.selectedIndividualId,
      'DemoIndividuals__row--clickable': true,
    };
  };

  selectIndividualFromList(item: Individual) {
    this.selectedIndividualId = item.id_individual;
    this.focusSelectedIndividualOnMap(true);
    this._cdr.markForCheck();
  }

  onMapIndividualSelected(individualId: number) {
    this.selectedIndividualId = individualId;
    this.focusSelectedIndividualOnMap(false);
    this.ensureSelectedIndividualPage(individualId);
    this._cdr.markForCheck();
  }

  deleteIndividual(item: Individual) {
    const confirmed = window.confirm(`Supprimer l'individu "${item.name_individual}" ?`);
    if (!confirmed) {
      return;
    }

    this._demoService
      .deleteIndividual(item.id_individual)
      .pipe(take(1))
      .subscribe(() => {
        if (this.selectedIndividualId === item.id_individual) {
          this.selectedIndividualId = null;
        }
        this.refreshPage();
        this.refreshMap();
        this._cdr.markForCheck();
      });
  }

  onGeometryDrawn(feature: { geometry?: GeoJsonGeometry | null } | null) {
    const geometry = feature?.geometry ?? null;
    const geomControl = this.form.get('geom');
    geomControl?.setValue(geometry);
    geomControl?.markAsTouched();
    geomControl?.markAsDirty();
  }

  clearGeometry(markAsDirty = true) {
    const geomControl = this.form.get('geom');
    geomControl?.setValue(null);
    geomControl?.markAsTouched();
    if (markAsDirty) {
      geomControl?.markAsDirty();
    }
    this.clearMapGeometry();
  }

  private resetForm() {
    this.form.reset({
      name_individual: '',
      cd_nom: null,
      observer: null,
      geom: null,
      additional_data: {
        age: null,
        sex: '',
        notes: '',
      },
    });
    this.form.markAsPristine();
    this.taxrefResults = [];
    this.clearMapGeometry();
  }

  private refreshPage() {
    this._pagination$.next(this._pagination$.getValue());
  }

  private refreshMap() {
    this._refreshMap$.next(this._refreshMap$.getValue() + 1);
  }

  private getCurrentFilters(): IndividualFilters {
    const value = this.filterForm.value;
    const observerValue = value.observer;
    const observer =
      observerValue === null || observerValue === undefined ? '' : String(observerValue).trim();

    return {
      name: (value.name ?? '').trim() || null,
      taxref: (value.taxref ?? '').trim() || null,
      observer: observer || null,
      date_from: (value.date_from ?? '').trim() || null,
      date_to: (value.date_to ?? '').trim() || null,
    };
  }

  private navigateToList(selectedId?: number) {
    const routeParent = this._route.parent as ActivatedRoute;
    this._router.navigate(['individuals'], {
      relativeTo: routeParent,
      queryParams: selectedId ? { selected: selectedId } : undefined,
    });
  }

  private clearMapGeometry() {
    if (!this._mapService?.map || !this._mapService?.leafletDrawFeatureGroup) {
      return;
    }
    this._mapService.removeAllLayers(
      this._mapService.map,
      this._mapService.leafletDrawFeatureGroup
    );
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

  private ensureSelectedIndividualPage(individualId: number) {
    if (this._listPaginationSnapshot?.items.some((item) => item.id_individual === individualId)) {
      return;
    }

    const pageState = this._pagination$.getValue();
    const index = this._allIndividualIds.indexOf(individualId);
    if (index < 0) {
      return;
    }

    const targetPage = Math.floor(index / pageState.limit) + 1;
    if (targetPage !== pageState.page) {
      this._pagination$.next({
        page: targetPage,
        limit: pageState.limit,
      });
    }
  }

  private focusSelectedIndividualOnMap(centerOnFeature: boolean) {
    if (this.selectedIndividualId === null) {
      return;
    }
    this._individualsMapComponent?.focusIndividual(this.selectedIndividualId, centerOnFeature);
  }

  private extractIndividualId(
    feature:
      | Partial<{
          id: unknown;
          properties: { id_individual?: unknown };
        }>
      | null
      | undefined
  ): number | null {
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
