import {Component} from '@angular/core';
import {TranslateModule} from '@ngx-translate/core';
import {TranslatorPipe} from '@app/shared/pipes/translate';

@Component({
    selector: 'src-operation',
    templateUrl: './operation.component.html',
    standalone: true,
    imports: [TranslateModule, TranslatorPipe],
})
export class OperationComponent {

}
