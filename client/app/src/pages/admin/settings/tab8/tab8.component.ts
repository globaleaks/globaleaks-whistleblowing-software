import {Component, OnInit, inject, input} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {Constants} from "@app/shared/constants/constants";
import {EnableEncryptionComponent} from "@app/shared/modals/enable-encryption/enable-encryption.component";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {SelectablesResolver} from "@app/shared/resolvers/selectables.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {SelectionEditorComponent, SelectionEntry} from "@app/shared/components/selection-editor/selection-editor.component";
import {UserProfile} from "@app/models/resolvers/user-resolver-model";
import {SelectableEntry, SelectableUser} from "@app/models/app/selectables";
import {HttpService} from "@app/shared/services/http.service";
import {TranslateModule} from "@ngx-translate/core";

@Component({
    selector: "src-tab8",
    templateUrl: "./tab8.component.html",
    standalone: true,
    imports: [FormsModule, SelectionEditorComponent, TranslateModule]
})
export class Tab8Component implements OnInit {
  protected authenticationService = inject(AuthenticationService);
  private readonly modalService = inject(NgbModal);
  private readonly appConfigService = inject(AppConfigService);
  private readonly utilsService = inject(UtilsService);
  protected nodeResolver = inject(NodeResolver);
  protected preferenceResolver = inject(PreferenceResolver);
  private readonly selectablesResolver = inject(SelectablesResolver);
  private readonly httpService = inject(HttpService);

  readonly contentForm = input.required<NgForm>();

  // Every administrator can read the entities offered by the choices, whatever
  // the areas it administers: they are served by their own endpoint
  userData: SelectableUser[] = [];
  userProfiles: UserProfile[] = [];
  questionnaireData: SelectableEntry[] = [];
  routeReload = false;

  protected readonly Constants = Constants;

  ngOnInit(): void {
    this.userData = this.selectablesResolver.dataModel.users;
    this.questionnaireData = this.selectablesResolver.dataModel.questionnaires;

    this.httpService.requestUserProfilesResource().subscribe((profiles: UserProfile[]) => {
      this.userProfiles = profiles.filter(profile => profile.name !== "");
    });
  }

  // The administrators authorized to change user passwords (i.e. holding the
  // key escrow) and, as options to add, the ones that could be authorized: an
  // encrypted admin other than the one performing the operation
  get currentUserId(): string {
    return this.authenticationService.session?.user_id || "";
  }

  get escrowAuthorized(): SelectionEntry[] {
    return this.userData
      .filter(user => user.escrow)
      .map(user => ({id: user.id, label: user.name}));
  }

  get escrowCandidates(): SelectionEntry[] {
    return this.userData
      .filter(user => user.role === "admin" && user.encryption && !user.escrow && user.id !== this.currentUserId)
      .map(user => ({id: user.id, label: user.name}));
  }

  // Adding and removing an authorization both toggle the escrow of the user
  toggleUserEscrow(userId: string): void {
    this.utilsService.runAdminOperation("toggle_user_escrow", {"value": userId}, true).subscribe(() => {
      this.selectablesResolver.refresh().subscribe(() => {
        this.userData = this.selectablesResolver.dataModel.users;
      });
    });
  }

  enableEncryption() {
    const node = this.nodeResolver.dataModel;
    node.encryption = false;
    const modalRef = this.modalService.open(EnableEncryptionComponent, { backdrop: 'static', keyboard: false });
    modalRef.result.then(() => {
      this.utilsService.runAdminOperation("enable_encryption", {}, false).subscribe(() => {
        this.authenticationService.logout();
      });
    }, () => { /* dismissed */ });
  }

  toggleEscrow(escrow: { checked: boolean }) {
    escrow.checked = this.nodeResolver.dataModel.escrow = !this.nodeResolver.dataModel.escrow;
    this.utilsService.runAdminOperation("toggle_escrow", {}, false).subscribe(() => {
      this.nodeResolver.dataModel.escrow = !this.nodeResolver.dataModel.escrow;
      this.selectablesResolver.refresh().subscribe(() => {
        this.userData = this.selectablesResolver.dataModel.users;
      });
    });
  }

  updateNode() {
    this.utilsService.update(this.nodeResolver.dataModel).subscribe(() => {
      this.appConfigService.reinit();
      if (this.routeReload) {
        this.utilsService.reloadCurrentRoute();
      } else {
        this.utilsService.reloadComponent();
      }
    });
  }

  resetSubmissions() {
    this.utilsService.deleteDialog();
  }

  enableRouteReload() {
    this.routeReload = true;
  }
}
