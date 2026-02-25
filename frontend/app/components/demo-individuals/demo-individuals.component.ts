import { ChangeDetectionStrategy, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BehaviorSubject, Observable, of, timer } from 'rxjs';
import { catchError, map, shareReplay, switchMap, take } from 'rxjs/operators';
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

import { GeoJsonGeometry, Individual } from '../../models/individual';
import { PaginatedResponse } from '../../models/pagination';
import { DemoService } from '../../services/demo.service';
import { TaxrefLite } from '../../models/taxref';

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
  imports: [CommonModule, ReactiveFormsModule, GN2CommonModule],
})
export class DemoIndividualsComponent implements OnInit {
  individuals$!: Observable<PaginatedResponse<Individual>>;
  saving = false;
  errorMessage: string | null = null;
  successMessage: string | null = null;
  editing: Individual | null = null;
  taxrefResults: TaxrefLite[] = [];
  taxrefLoading = false;
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

  form = this._fb.group({
    name_individual: this._fb.control<string>('', [Validators.required, Validators.maxLength(80)]),
    cd_nom: this._fb.control<number | null>(null, [Validators.required, positiveIntegerValidator()]),
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

  constructor(
    private _demoService: DemoService,
    private _fb: FormBuilder,
    private _mapService: MapService
  ) {}

  ngOnInit() {
    this.individuals$ = this._pagination$.pipe(
      switchMap(({ page, limit }) => this._demoService.getIndividuals(page, limit)),
      shareReplay({ bufferSize: 1, refCount: true })
    );
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
    const sex = typeof additionalData.sex === 'string' ? additionalData.sex.trim() : additionalData.sex;
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
    const payload = {
      name_individual: this.form.value.name_individual ?? '',
      cd_nom: this.form.value.cd_nom ? Number(this.form.value.cd_nom) : null,
      geom: this.form.value.geom ?? null,
      additional_data: payloadAdditionalData,
    };
    const request$ = this.editing
      ? this._demoService.updateIndividual(this.editing.id_individual, payload)
      : this._demoService.createIndividual(payload);
    request$.pipe(take(1)).subscribe({
      next: () => {
        this.successMessage = this.editing
          ? "L'individu a ete mis a jour."
          : "L'individu a ete ajoute.";
        this.saving = false;
        this.editing = null;
        this.resetForm();
        this.refreshPage();
      },
      error: (err) => {
        this.errorMessage = err?.message || 'Erreur lors de la sauvegarde.';
        this.saving = false;
      },
    });
  }

  startEdit(item: Individual) {
    this.editing = item;
    this.successMessage = null;
    this.errorMessage = null;
    this.form.patchValue({
      name_individual: item.name_individual,
      cd_nom: item.cd_nom,
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
    this.editing = null;
    this.successMessage = null;
    this.errorMessage = null;
    this.resetForm();
  }

  nextPage(payload: PaginatedResponse<Individual>) {
    if (!payload.next_num) {
      return;
    }
    this._pagination$.next({ page: payload.next_num, limit: payload.per_page });
  }

  prevPage(payload: PaginatedResponse<Individual>) {
    if (!payload.prev_num) {
      return;
    }
    this._pagination$.next({ page: payload.prev_num, limit: payload.per_page });
  }

  deleteIndividual(item: Individual) {
    const confirmed = window.confirm(`Supprimer l'individu "${item.name_individual}" ?`);
    if (!confirmed) {
      return;
    }
    this._demoService
      .deleteIndividual(item.id_individual)
      .pipe(take(1))
      .subscribe(() => this.refreshPage());
  }

  trackByIndividualId(index: number, item: Individual) {
    return item.id_individual;
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

  private clearMapGeometry() {
    if (!this._mapService?.map || !this._mapService?.leafletDrawFeatureGroup) {
      return;
    }
    this._mapService.removeAllLayers(this._mapService.map, this._mapService.leafletDrawFeatureGroup);
  }
}
