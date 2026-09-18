import {Component, computed, contentChildren, inject, linkedSignal} from "@angular/core";
import {ActivatedRoute} from "@angular/router";
import {TranslatePipe} from "@ngx-translate/core";
import {NgTemplateOutlet} from "@angular/common";
import {NgbNav, NgbNavContent, NgbNavItem, NgbNavItemRole, NgbNavLinkBase, NgbNavLinkButton, NgbNavOutlet} from "@ng-bootstrap/ng-bootstrap";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";

/**
 * Tabbed container driven by the <ng-template srcTab> declared in its content.
 *
 * The tab list is a signal derived from the content query, so it is available
 * on first rendering and reacts to visibility changes without any lifecycle
 * hook, timer or manual change detection.
 */
@Component({
  selector: "src-tabs",
  standalone: true,
  imports: [TranslatePipe, NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgbNavOutlet, NgTemplateOutlet],
  template: `
    <ul ngbNav #nav="ngbNav" class="nav-tabs" [activeId]="active()" (activeIdChange)="active.set($event)">
      @for (tab of tabs(); track tab.id()) {
        <li [ngbNavItem]="tab.id()">
          <button type="button" ngbNavLink [attr.data-cy]="tab.id()">
            @if (tab.icon()) {
              <i [class]="tab.icon()"></i>
            }
            <span>{{ tab.title() | translate }}</span>
          </button>
          <ng-template ngbNavContent>
            <ng-container *ngTemplateOutlet="tab.template"></ng-container>
          </ng-template>
        </li>
      }
    </ul>
    <div [ngbNavOutlet]="nav" class="mt-2"></div>
  `
})
export class TabsComponent {
  private readonly activatedRoute = inject(ActivatedRoute);

  private readonly declared = contentChildren(TabDirective);

  protected readonly tabs = computed(() => this.declared().filter(tab => tab.visible()));

  // The tab a link asks for, read where the page is entered: a mail pointing at
  // one tab of a page opens that tab.
  private readonly requested = this.activatedRoute.snapshot.queryParamMap.get("tab") || "";

  // The tab asked for, else the first visible one; user selection wins until
  // the list changes.
  protected readonly active = linkedSignal(() => {
    const tabs = this.tabs();

    return tabs.find(tab => tab.id() === this.requested)?.id() ?? tabs[0]?.id();
  });
}
