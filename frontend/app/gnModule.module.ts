import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Routes, RouterModule } from '@angular/router';
import { HttpClientXsrfModule } from '@angular/common/http';
import { GN2CommonModule } from '@geonature_common/GN2Common.module';
import { NgbModule } from '@ng-bootstrap/ng-bootstrap';

import { DemoFormGuard } from './guards/demo-form.guard';
import { DemoIdGuard } from './guards/demo-id.guard';
import { DemoResolver } from './guards/demo-resolver';
import { DemoService } from './services/demo.service';
import { DemoStateService } from './services/demo-state.service';
import { DemoFormComponent } from './components/demo-form/demo-form.component';
import { DemoIndividualsComponent } from './components/demo-individuals/demo-individuals.component';
import { DemoLabComponent } from './components/demo-lab/demo-lab.component';
import { DemoListComponent } from './components/demo-list/demo-list.component';
import { DemoPageComponent } from './components/demo-page/demo-page.component';
import { DemoResolvedComponent } from './components/demo-resolved/demo-resolved.component';
import { DemoRxjsComponent } from './components/demo-rxjs/demo-rxjs.component';
import { DemoStateComponent } from './components/demo-state/demo-state.component';
import { DemoTabsComponent } from './components/demo-tabs/demo-tabs.component';

export const routes: Routes = [
  {
    path: "",
    component: DemoTabsComponent,
    children: [
      {
        path: "",
        redirectTo: "list",
        pathMatch: "full",
      },
      {
        path: "list",
        component: DemoListComponent,
      },
      {
        path: "individuals/new",
        component: DemoIndividualsComponent,
      },
      {
        path: "individuals/:id/edit",
        component: DemoIndividualsComponent,
      },
      {
        path: "individuals",
        component: DemoIndividualsComponent,
      },
      {
        path: "lab",
        component: DemoLabComponent,
        children: [
          {
            path: "",
            redirectTo: "forms",
            pathMatch: "full",
          },
          {
            path: "forms",
            component: DemoFormComponent,
            canDeactivate: [DemoFormGuard],
          },
          {
            path: "rxjs",
            component: DemoRxjsComponent,
          },
          {
            path: "state",
            component: DemoStateComponent,
          },
        ],
      },
    ],
  },
  {
    path: "resolved/:id_demo",
    component: DemoResolvedComponent,
    canActivate: [DemoIdGuard],
    resolve: { demo: DemoResolver },
  },
  {
    path: ":id_demo",
    component: DemoPageComponent,
    canActivate: [DemoIdGuard],
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
    DemoListComponent,
    DemoPageComponent,
    DemoFormComponent,
    DemoIndividualsComponent,
    DemoLabComponent,
    DemoResolvedComponent,
    DemoRxjsComponent,
    DemoStateComponent,
    DemoTabsComponent
  ],
  providers: [DemoService, DemoStateService, DemoIdGuard, DemoFormGuard, DemoResolver],
  bootstrap: [],
})
export class GeonatureModule {}
