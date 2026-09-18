import {Component, ChangeDetectionStrategy} from "@angular/core";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    changeDetection: ChangeDetectionStrategy.OnPush,
    selector: "src-demo",
    templateUrl: "./demo.component.html",
    standalone: true,
    imports: [TranslateModule]
})
export class DemoComponent {

}
