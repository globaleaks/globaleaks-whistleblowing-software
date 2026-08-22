import {Component, ChangeDetectionStrategy} from "@angular/core";

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-blank",
    templateUrl: "./blank.component.html",
    standalone: true
})
export class BlankComponent {

}
