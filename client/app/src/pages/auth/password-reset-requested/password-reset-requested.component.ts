import {Component, ChangeDetectionStrategy} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-password-reset-requested",
    templateUrl: "./password-reset-requested.component.html",
    standalone: true,
    imports: [TranslatePipe]
})
export class PasswordRequestedComponent {

}
