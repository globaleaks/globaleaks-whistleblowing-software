import {Component, OnInit, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {preferenceResolverModel} from "@app/models/resolvers/preference-resolver-model";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {UserHomeComponent} from "../../../shared/partials/user-home/user-home.component";

@Component({
    selector: "src-custodian-home",
    templateUrl: "./home.component.html",
    standalone: true,
    imports: [UserHomeComponent]
})
export class HomeComponent implements OnInit {
  private appDataService = inject(AppDataService);
  private utilsService = inject(UtilsService);
  private preference = inject(PreferenceResolver);

  preferenceData:  preferenceResolverModel;

  ngOnInit(): void {
    if (this.preference.dataModel) {
      this.preferenceData = this.preference.dataModel;
    }
    if (this.appDataService.public.node.user_privacy_policy_text && this.preferenceData.accepted_privacy_policy === "1970-01-01T00:00:00Z") {
      this.utilsService.acceptPrivacyPolicyDialog().subscribe();
    }
  }
}
