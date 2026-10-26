import {Component} from "@angular/core";
import {RouterLink, RouterLinkActive} from "@angular/router";
import {TranslatePipe} from "@ngx-translate/core";

@Component({
    selector: "src-auditor-sidebar",
    templateUrl: "./sidebar.component.html",
    standalone: true,
    imports: [RouterLink, RouterLinkActive, TranslatePipe]
})
export class AuditorSidebarComponent {

}
