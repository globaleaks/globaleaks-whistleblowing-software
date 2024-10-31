import {Component} from "@angular/core";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-demo",
    templateUrl: "./demo.component.html",
    standalone: true,
    imports: [TranslateModule, TranslatorPipe]
})
export class DemoComponent {

}
