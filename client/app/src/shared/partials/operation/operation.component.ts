import {Component, ChangeDetectionStrategy} from '@angular/core';
import {TranslateModule} from '@ngx-translate/core';

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: 'src-operation',
    templateUrl: './operation.component.html',
    standalone: true,
    imports: [TranslateModule],
})
export class OperationComponent {

}
