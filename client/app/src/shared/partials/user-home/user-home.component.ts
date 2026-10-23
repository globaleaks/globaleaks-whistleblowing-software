import {Component} from "@angular/core";
import {UserWarningsComponent} from "../user-warnings/user-warnings.component";
import {TranslatePipe} from "@ngx-translate/core";

@Component({
    selector: "src-user-home",
    templateUrl: "./user-home.component.html",
    standalone: true,
    imports: [UserWarningsComponent, TranslatePipe]
})
export class UserHomeComponent {
}
