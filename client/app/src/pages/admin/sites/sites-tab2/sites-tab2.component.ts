import {Component, OnInit} from "@angular/core";
import {QuestionnairesResolver} from "@app/shared/resolvers/questionnaires.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";

@Component({
  selector: "src-sites-tab2",
  templateUrl: "./sites-tab2.component.html"
})
export class SitesTab2Component implements OnInit {

  initialValues = {
    enable_signup: false,
    signup_tos1_enable: false,
    signup_tos2_enable: false
  };

  constructor(protected nodeResolver: NodeResolver, protected utilsService: UtilsService, public questionnairesResolver: QuestionnairesResolver) {
  }

  ngOnInit() {
    this.initialValues.enable_signup = this.nodeResolver.dataModel.enable_signup;
    this.initialValues.signup_tos1_enable = this.nodeResolver.dataModel.signup_tos1_enable;
    this.initialValues.signup_tos2_enable = this.nodeResolver.dataModel.signup_tos2_enable;
  }

  onModeChange() {
    if (this.nodeResolver.dataModel.mode === 'accreditation') {
      this.nodeResolver.dataModel.enable_signup = false;
      this.nodeResolver.dataModel.signup_tos1_enable = true;
      this.nodeResolver.dataModel.signup_tos2_enable = true;
    } else {
      this.nodeResolver.dataModel.enable_signup = this.initialValues.enable_signup;
      this.nodeResolver.dataModel.signup_tos1_enable = this.initialValues.signup_tos1_enable;
      this.nodeResolver.dataModel.signup_tos2_enable = this.initialValues.signup_tos2_enable;
    }
  }
}