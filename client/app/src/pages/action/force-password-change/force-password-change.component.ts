import {Component} from "@angular/core";
import { PasswordChangeComponent } from "../../../shared/partials/password-change/password-change.component";
import { TranslateModule } from "@ngx-translate/core";
import { TranslatorPipe } from "@app/shared/pipes/translate";

@Component({
    selector: "src-force-password-change",
    templateUrl: "./force-password-change.component.html",
    standalone: true,
    imports: [PasswordChangeComponent, TranslateModule, TranslatorPipe]
})
export class ForcePasswordChangeComponent {

}