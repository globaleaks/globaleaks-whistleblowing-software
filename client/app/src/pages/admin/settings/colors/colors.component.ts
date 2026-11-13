import {Component, inject, signal} from "@angular/core";
import {TranslatePipe} from "@ngx-translate/core";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {OFFICIAL_PRIMARY_COLOR, normalizeHexColor} from "@app/shared/theme/palette";

/**
 * The colors of the site: its primary color, from which the palette of the whole interface is
 * computed
 *
 * The page shows the color as it is chosen; the palette the interface takes from it is the closest
 * accessible one (palette.ts). The color goes in the node with the other settings, and the site
 * takes it only once they are saved.
 */
@Component({
  selector: "src-colors",
  templateUrl: "./colors.component.html",
  standalone: true,
  imports: [NgbTooltipModule, TranslatePipe]
})
export class ColorsComponent {
  private readonly nodeResolver = inject(NodeResolver);

  protected readonly officialColor = OFFICIAL_PRIMARY_COLOR;

  protected readonly color = signal(this.nodeResolver.dataModel.primary_color || OFFICIAL_PRIMARY_COLOR);

  // The picker of the browser, opened by the button it sits under; where showPicker is missing, the
  // click on the input opens it the same
  protected openPicker(input: HTMLInputElement): void {
    if (typeof input.showPicker === "function") {
      input.showPicker();
    } else {
      input.click();
    }
  }

  // The picker of the browser gives the color as #rrggbb
  protected onColor(event: Event): void {
    const color = normalizeHexColor((event.target as HTMLInputElement).value);
    if (color !== null) {
      this.setColor(color);
    }
  }

  protected reset(): void {
    this.setColor(OFFICIAL_PRIMARY_COLOR);
  }

  private setColor(color: string): void {
    this.color.set(color);
    this.nodeResolver.dataModel.primary_color = color;
  }
}
