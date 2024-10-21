import {Component} from "@angular/core";
import { PreferencesComponent } from "../../../shared/partials/preferences/preferences.component";

@Component({
    selector: "src-admin-preferences",
    templateUrl: "./admin-preferences.component.html",
    standalone: true,
    imports: [PreferencesComponent]
})
export class AdminPreferencesComponent {

}