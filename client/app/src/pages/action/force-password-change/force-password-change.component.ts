import {Component} from "@angular/core";
import {PasswordChangeComponent} from "@app/shared/partials/password-change/password-change.component";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-force-password-change",
    templateUrl: "./force-password-change.component.html",
    standalone: true,
    imports: [PasswordChangeComponent, TranslateModule]
})
export class ForcePasswordChangeComponent {

}