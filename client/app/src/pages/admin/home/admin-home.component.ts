import {Component, OnInit, inject} from "@angular/core";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {preferenceResolverModel} from "@app/models/resolvers/preference-resolver-model";
import {UtilsService} from "@app/shared/services/utils.service";
import {TabsComponent} from "@app/shared/components/tabs/tabs.component";
import {TabDirective} from "@app/shared/components/tabs/tab.directive";
import {UserHomeComponent} from "@app/shared/partials/user-home/user-home.component";
import {ChangelogComponent} from "@app/pages/admin/home/changelog/changelog.component";
import {LicenseComponent} from "@app/pages/admin/home/license/license.component";


@Component({
    selector: "src-admin-home",
    templateUrl: "./admin-home.component.html",
    standalone: true,
    imports: [TabsComponent, TabDirective, UserHomeComponent, ChangelogComponent, LicenseComponent]
})
export class adminHomeComponent implements OnInit {
  private utilsService = inject(UtilsService);
  private preference = inject(PreferenceResolver);
  protected nodeResolver = inject(NodeResolver);

  nodeData: nodeResolverModel;
  preferenceData: preferenceResolverModel;

  ngOnInit(): void {
    if (this.nodeResolver.dataModel) {
      this.nodeData = this.nodeResolver.dataModel;
    }
    if (this.preference.dataModel) {
      this.preferenceData = this.preference.dataModel;
    }
    if (this.nodeData.user_privacy_policy_text && this.preferenceData.accepted_privacy_policy === "1970-01-01T00:00:00Z") {
      this.utilsService.acceptPrivacyPolicyDialog().subscribe();
    }
  }
}
