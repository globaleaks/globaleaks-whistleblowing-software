import {Component, ChangeDetectionStrategy} from "@angular/core";

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-profile",
    templateUrl: "./profile.component.html",
    standalone: true
})
export class ProfileComponent {

}
