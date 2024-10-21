import {Component} from "@angular/core";
import {UserWarningsComponent} from "../user-warnings/user-warnings.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-user-home",
    templateUrl: "./user-home.component.html",
    standalone: true,
    imports: [UserWarningsComponent, TranslateModule, TranslatorPipe]
})
export class UserHomeComponent {
}
