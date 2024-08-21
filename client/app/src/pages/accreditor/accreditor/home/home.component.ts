import {Component} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {preferenceResolverModel} from "@app/models/resolvers/preference-resolver-model";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {UtilsService} from "@app/shared/services/utils.service";


@Component({
  selector: "src-accreditor-home",
  templateUrl: "./home.component.html"
})
export class AccreditorHomeComponent {
  preferenceData:  preferenceResolverModel;
  constructor(private appDataService: AppDataService,private utilsService: UtilsService, private preference: PreferenceResolver) {
  }

  ngOnInit(): void {
    if (this.preference.dataModel) {
      this.preferenceData = this.preference.dataModel;
    }
    if (this.appDataService.public.node.user_privacy_policy_text && this.preferenceData.accepted_privacy_policy === "1970-01-01T00:00:00Z") {
      this.utilsService.acceptPrivacyPolicyDialog().subscribe();
    }
  }
}
