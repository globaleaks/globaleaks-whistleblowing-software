import { Component, Input } from '@angular/core';
import { RFile } from '@app/models/app/shared-public-model';
import { ReceiverTipService } from '@app/services/helper/receiver-tip.service';
import { PreferenceResolver } from '@app/shared/resolvers/preference.resolver';
import { UtilsService } from '@app/shared/services/utils.service';

@Component({
  selector: 'src-tip-oe-rfiles-receiver',
  templateUrl: './tip-oe-rfiles-receiver.component.html'
})
export class TipOeRfilesReceiverComponent {

  @Input() key: string;

  collapsed = false;

  constructor(protected utilsService: UtilsService, protected tipService: ReceiverTipService, protected preferenceResolver: PreferenceResolver,) {
  }


  getSortedRFiles(data: RFile[]): RFile[] {
    return data;
  }


}
