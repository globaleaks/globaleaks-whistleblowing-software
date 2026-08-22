import {Component, ChangeDetectionStrategy} from "@angular/core";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-password-reset-requested",
    templateUrl: "./password-reset-requested.component.html",
    standalone: true,
    imports: [TranslateModule]
})
export class PasswordRequestedComponent {

}
