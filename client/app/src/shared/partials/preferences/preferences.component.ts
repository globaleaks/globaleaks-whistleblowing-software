import {Component} from "@angular/core";
import {PreferenceTab1Component} from "@app/shared/partials/preference-tabs/preference-tab1/preference-tab1.component";
import {PreferenceTab2Component} from "@app/shared/partials/preference-tabs/preference-tab2/preference-tab2.component";
import {NgbNav, NgbNavItem, NgbNavLink} from "@ng-bootstrap/ng-bootstrap";

import {PreferenceTab1Component as PreferenceTab1Component_1} from "../preference-tabs/preference-tab1/preference-tab1.component";
import {PreferenceTab2Component as PreferenceTab2Component_1} from "../preference-tabs/preference-tab2/preference-tab2.component";
import {TranslateModule} from "@ngx-translate/core";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-preferences",
    templateUrl: "./preferences.component.html",
    standalone: true,
    imports: [NgbNav, NgbNavItem, NgbNavLink, PreferenceTab1Component_1, PreferenceTab2Component_1, TranslateModule, TranslatorPipe]
})
export class PreferencesComponent {
  activeTab: string = "tab1";

  tabs = [
    {
      id: "tab1",
      title: "Preferences",
      component: PreferenceTab1Component
    },
    {
      id: "tab2",
      title: "Password",
      component: PreferenceTab2Component
    }
  ];
}