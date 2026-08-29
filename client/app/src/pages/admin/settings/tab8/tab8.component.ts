import {Component, OnInit, computed, inject, input} from "@angular/core";
import {NgForm, FormsModule} from "@angular/forms";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {Constants} from "@app/shared/constants/constants";
import {EnableEncryptionComponent} from "@app/shared/modals/enable-encryption/enable-encryption.component";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {ContextsResolver} from "@app/shared/resolvers/contexts.resolver";
import {QuestionnairesResolver} from "@app/shared/resolvers/questionnaires.resolver";
import {UsersResolver} from "@app/shared/resolvers/users.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {SelectionEditorComponent, SelectionEntry} from "@app/shared/components/selection-editor/selection-editor.component";
import {UserProfile} from "@app/models/resolvers/user-resolver-model";
import {contextResolverModel} from "@app/models/resolvers/context-resolver-model";
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
  private modalService = inject(NgbModal);
  private appConfigService = inject(AppConfigService);
  private utilsService = inject(UtilsService);
  protected nodeResolver = inject(NodeResolver);
  protected preferenceResolver = inject(PreferenceResolver);
  private usersResolver = inject(UsersResolver);
  private contextsResolver = inject(ContextsResolver);
  private questionnairesResolver = inject(QuestionnairesResolver);
  private httpService = inject(HttpService);

  readonly contentForm = input.required<NgForm>();
  readonly questionnaireData = computed(() => this.questionnairesResolver.resource.value());
  readonly contextsData = computed<contextResolverModel[]>(() => {
    const contexts = this.contextsResolver.resource.value();
    return Array.isArray(contexts) ? contexts : [contexts];
  });

  userProfiles: UserProfile[] = [];
  routeReload = false;

  protected readonly Constants = Constants;

  ngOnInit(): void {
    this.httpService.requestUserProfilesResource().subscribe((profiles: UserProfile[]) => {
      this.userProfiles = profiles.filter(profile => profile.name !== "");
    });
  }

  isManagementSession(): boolean {
    return this.nodeResolver.dataModel.tid === 1 ||
      !!this.authenticationService.session?.properties?.management_session;
  }

  get acceptForwardingFrom(): string {
    return (this.nodeResolver.dataModel.accept_forwarding_from || []).join(", ");
  }

  set acceptForwardingFrom(value: string) {
    this.nodeResolver.dataModel.accept_forwarding_from = value.split(",")
      .map(entry => entry.trim())
      .filter(entry => entry !== "")
      .map(entry => entry === "*" ? entry : Number(entry));
  }

  // The administrators authorized to change user passwords (i.e. holding the
  // key escrow) and, as options to add, the ones that could be authorized: an
  // encrypted admin other than the one performing the operation
  get currentUserId(): string {
    return this.authenticationService.session?.user_id || "";
  }

  readonly escrowAuthorized = computed<SelectionEntry[]>(() => this.usersResolver.resource.value()
    .filter(user => user.escrow)
    .map(user => ({id: user.id, label: user.name})));

  readonly escrowCandidates = computed<SelectionEntry[]>(() => this.usersResolver.resource.value()
    .filter(user => user.role === "admin" && user.encryption && !user.escrow && user.id !== this.currentUserId)
    .map(user => ({id: user.id, label: user.name})));

  // Adding and removing an authorization both toggle the escrow of the user
  toggleUserEscrow(userId: string) {
    this.utilsService.runAdminOperation("toggle_user_escrow", {"value": userId}, false).subscribe(() => {
      this.usersResolver.refresh();
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
    });
  }

  toggleEscrow(escrow: { checked: boolean }) {
    escrow.checked = this.nodeResolver.dataModel.escrow = !this.nodeResolver.dataModel.escrow;
    this.utilsService.runAdminOperation("toggle_escrow", {}, false).subscribe(() => {
      this.nodeResolver.dataModel.escrow = !this.nodeResolver.dataModel.escrow;
      this.usersResolver.refresh();
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
