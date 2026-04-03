import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Routes, RouterModule } from '@angular/router';
import { HttpClientXsrfModule } from '@angular/common/http';
import { GN2CommonModule } from '@geonature_common/GN2Common.module';
import { NgbModule } from '@ng-bootstrap/ng-bootstrap';

import { IndividualService } from './services/individual.service';
import { IndividualListComponent } from './components/individual-list/individual-list.component';
import { IndividualDetailComponent } from './components/individual-detail/individual-detail.component';
import { IndividualFormComponent } from './components/individual-form/individual-form.component';

export const routes: Routes = [
  {
    path: "form",
    children: [
      {
        path: "",
        component: IndividualFormComponent,
      },
      {
        path: ":id_individual",
        component: IndividualFormComponent,
      }
    ]
  },
  {
    path: "",
    children: [
      {
        path: "",
        component: IndividualListComponent,
      },
      {
        path: ":id_individual",
        component: IndividualDetailComponent,
      }
    ]
  },
];

@NgModule({
  imports: [
    HttpClientXsrfModule.withOptions({
      cookieName: 'token',
      headerName: 'token',
    }),
    CommonModule,
    GN2CommonModule,
    NgbModule,
    RouterModule.forChild(routes),

    // Module component
    IndividualDetailComponent,
    IndividualListComponent,
    IndividualFormComponent
  ],
  providers: [IndividualService],
  bootstrap: [],
})
export class GeonatureModule {}
