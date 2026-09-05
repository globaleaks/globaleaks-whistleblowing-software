import {Component, inject} from "@angular/core";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {FormsModule} from "@angular/forms";
import {Tab1Component} from "@app/pages/admin/settings/tab1/tab1.component";
import {Router} from "@angular/router";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";

@Component({
    selector: "src-recipient-settings",
    templateUrl: "./settings.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, FormsModule, Tab1Component]
})
export class RecipientSettingsComponent {
  private readonly preferenceResolver = inject(PreferenceResolver);
  private readonly router = inject(Router);

  constructor() {
    if (!this.preferenceResolver.dataModel.profile.permissions.can_manage_settings) {
      this.router.navigate(['recipient/home']).then();
    }
  }
}
