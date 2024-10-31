import {AfterViewInit, ChangeDetectorRef, Component, TemplateRef, ViewChild, inject} from "@angular/core";
import {Router} from "@angular/router";
import {Tab} from "@app/models/component-model/tab";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {Tab1Component} from "@app/pages/admin/settings/tab1/tab1.component";
import {FormsModule} from "@angular/forms";
import {NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgbNavOutlet} from "@ng-bootstrap/ng-bootstrap";
import {NgTemplateOutlet} from "@angular/common";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-recipient-settings",
    templateUrl: "./settings.component.html",
    standalone: true,
    imports: [FormsModule, NgbNav, NgbNavItem, NgbNavItemRole, NgbNavLinkButton, NgbNavLinkBase, NgbNavContent, NgTemplateOutlet, NgbNavOutlet, Tab1Component, TranslateModule, TranslatorPipe]
})
export class RecipientSettingsComponent implements AfterViewInit {
  private cdr = inject(ChangeDetectorRef);
  private preferenceResolver = inject(PreferenceResolver);
  private router = inject(Router);

  @ViewChild("tab1") tab1!: TemplateRef<Tab1Component>;
  tabs: Tab[];
  active: string;

  constructor() {
    if (!this.preferenceResolver.dataModel.can_edit_general_settings) {
      this.router.navigate(['recipient/home']).then();
    }
  }

  ngAfterViewInit(): void {
    this.active = "Settings";

    this.tabs = [
      {
        title: "Settings",
        component: this.tab1
      },
    ];
    this.cdr.detectChanges();
  }
}

