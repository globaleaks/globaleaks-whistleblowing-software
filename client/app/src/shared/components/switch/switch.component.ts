import {Component, input, model, output, ChangeDetectionStrategy} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {TranslatePipe} from '@ngx-translate/core';

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: 'app-switch',
    templateUrl: './switch.component.html',
    standalone: true,
    imports: [FormsModule, TranslatePipe]
})
export class SwitchComponent {
  readonly label = input('Switch');
  readonly isChecked = input(false);
  readonly can_upload_files = model<boolean>();
  readonly switchChange = output<boolean>();

}
