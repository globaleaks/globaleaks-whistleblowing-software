import { Component, Input } from '@angular/core';
import { AppDataService } from '@app/app-data.service';
import { RFile } from '@app/models/app/shared-public-model';
import { ReceiverTipService } from '@app/services/helper/receiver-tip.service';
import { PreferenceResolver } from '@app/shared/resolvers/preference.resolver';
import { UtilsService } from '@app/shared/services/utils.service';

@Component({
  selector: 'src-tip-eo-rfiles-receiver',
  templateUrl: './tip-eo-rfiles-receiver.component.html'
})
export class TipEoRfilesReceiverComponent {

  @Input() key: string;

  collapsed = false;

  constructor(protected utilsService: UtilsService, protected tipService: ReceiverTipService,
              protected preferenceResolver: PreferenceResolver, protected readonly appDataService: AppDataService) {
  }


  getSortedRFiles(data: RFile[]): RFile[] {
    return data;
  }


}
