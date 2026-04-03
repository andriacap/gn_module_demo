import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

import { GN2CommonModule } from '@geonature_common/GN2Common.module';
import { ConfigService } from '@geonature/services/config.service';

import {
  Individual,
} from '../../models/individual';

@Component({
  standalone: true,
  selector: 'pnx-individual',
  templateUrl: 'individual.component.html',
  styleUrls: ['./individual.component.scss'],
  imports: [
    GN2CommonModule,
    CommonModule,
  ],
})
export class IndividualComponent {
  @Input()
  individual: Individual | null = null;

  constructor(private _configService: ConfigService)
  {}
}
