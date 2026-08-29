import {Component, computed, contentChildren, linkedSignal} from "@angular/core";
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
  private readonly declared = contentChildren(TabDirective);

  protected readonly tabs = computed(() => this.declared().filter(tab => tab.visible()));

  // The first visible tab by default. A tab chosen stays chosen while it is visible: a tab
  // appearing or disappearing - the one of the registrations, as the registration is enabled -
  // does not take the reader elsewhere.
  protected readonly active = linkedSignal<TabDirective[], string | undefined>({
    source: this.tabs,
    computation: (tabs, previous) => {
      if (previous && tabs.some(tab => tab.id() === previous.value)) {
        return previous.value;
      }

      return tabs[0]?.id();
    }
  });
}
