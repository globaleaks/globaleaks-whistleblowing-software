import {Component, input, model, output} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {TranslateModule} from '@ngx-translate/core';

@Component({
    selector: 'app-switch',
    templateUrl: './switch.component.html',
    standalone: true,
    imports: [FormsModule, TranslateModule]
})
export class SwitchComponent {
  readonly label = input('Switch');
  readonly isChecked = input(false);
  readonly can_upload_files = model<boolean>();
  readonly switchChange = output<boolean>();

}
