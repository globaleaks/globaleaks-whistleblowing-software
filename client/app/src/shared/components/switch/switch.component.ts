import {Component, Input, Output, EventEmitter} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {TranslateModule} from '@ngx-translate/core';
import {TranslatorPipe} from '@app/shared/pipes/translate';

@Component({
    selector: 'app-switch',
    templateUrl: './switch.component.html',
    standalone: true,
    imports: [FormsModule, TranslateModule, TranslatorPipe]
})
export class SwitchComponent {
  @Input() label: string = 'Switch';
  @Input() isChecked: boolean = false;
  @Input() can_upload_files:boolean
  @Output() switchChange = new EventEmitter<boolean>();

}
