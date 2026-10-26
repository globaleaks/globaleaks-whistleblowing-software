import {Component, ChangeDetectionStrategy} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-demo",
    templateUrl: "./demo.component.html",
    standalone: true,
    imports: [TranslatePipe]
})
export class DemoComponent {

}
