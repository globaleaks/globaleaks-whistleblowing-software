import {Component, inject} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";

@Component({
    selector: "src-changelog",
    templateUrl: "./changelog.component.html",
    standalone: true,
    imports: [TranslatePipe]
})
export class ChangelogComponent {
  protected nodeResolver = inject(NodeResolver);
}
