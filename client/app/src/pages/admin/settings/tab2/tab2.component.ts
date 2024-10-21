import {Component, ElementRef, Input, OnInit, ViewChild, inject} from "@angular/core";
import {NgForm} from "@angular/forms";
import * as Flow from "@flowjs/flow.js";
import type {FlowFile} from "@flowjs/flow.js";
import {FlowDirective} from "@flowjs/ngx-flow";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {preferenceResolverModel} from "@app/models/resolvers/preference-resolver-model";
import {AdminFile} from "@app/models/component-model/admin-file";
import {NgClass} from "@angular/common";
import {AdminFileComponent} from "../../../../shared/partials/admin-file/admin-file.component";
import {SwitchComponent} from "../../../../shared/components/switch/switch.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {TranslateModule} from "@ngx-translate/core";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";


@Component({
    selector: "src-tab2",
    templateUrl: "./tab2.component.html",
    standalone: true,
    imports: [NgbTooltipModule, NgClass, AdminFileComponent, SwitchComponent, TranslatorPipe, OrderByPipe, TranslateModule]
})
export class Tab2Component implements OnInit {
  private appConfigService = inject(AppConfigService);
  private preferenceResolver = inject(PreferenceResolver);
  private utilsService = inject(UtilsService);
  private nodeResolver = inject(NodeResolver);
  private authenticationService = inject(AuthenticationService);

  @Input() contentForm: NgForm;
  @ViewChild("flowAdvanced", {static: true}) flowAdvanced: FlowDirective;
  @ViewChild("uploader") uploaderInput: ElementRef;

  files: FlowFile[] = [];
  flow: FlowDirective;
  preferenceData: preferenceResolverModel;
  authenticationData: AuthenticationService;
  permissionStatus = false;

  admin_files: AdminFile[] = [
    {
      "title": "Favicon",
      "varname": "favicon",
      "filename": "custom_favicon.ico",
      "size": "200000"
    },
    {
      "title": "CSS",
      "varname": "css",
      "filename": "custom_stylesheet.css",
      "size": "10000000"
    },
    {
      "title": "JavaScript",
      "varname": "script",
      "filename": "custom_script.js",
      "size": "10000000"
    }
  ];

  ngOnInit(): void {
    this.preferenceData = this.preferenceResolver.dataModel;
    this.authenticationData = this.authenticationService;
    this.authenticationData.permissions = {
      can_upload_files: false
    };
    this.preferenceData.permissions = {
      can_upload_files: false
    };
    this.updateFiles();
    this.permissionStatus = this.authenticationData.session.permissions.can_upload_files;
  }

  onFileSelected(files: FileList | null) {
    if (files && files.length > 0) {
      const file = files[0];
      const flowJsInstance = this.utilsService.flowDefault;

      flowJsInstance.opts.target = "api/admin/files/custom";
      flowJsInstance.opts.allowDuplicateUploads = true;
      flowJsInstance.opts.singleFile = true;
      flowJsInstance.opts.query = {fileSizeLimit: this.nodeResolver.dataModel.maximum_filesize * 1024 * 1024};
      flowJsInstance.opts.headers = {"X-Session": this.authenticationService.session.id};
      
      flowJsInstance.on("fileSuccess", (_) => {
        this.appConfigService.reinit(false);
        this.utilsService.reloadComponent();
      });
      flowJsInstance.on("fileError", (_) => {
        if (this.uploaderInput) {
          this.uploaderInput.nativeElement.value = "";
        }
      });
      this.utilsService.onFlowUpload(flowJsInstance, file)
    }
  }

  canUploadFiles() {
    return this.authenticationData.session.permissions.can_upload_files;
  }

  deleteFile(url: string): void {
    this.utilsService.deleteFile(url).subscribe(
      () => {
        this.updateFiles();
        this.utilsService.reloadComponent();
      }
    );
  }

  updateFiles(): void {
    this.utilsService.getFiles().subscribe(
      (updatedFiles) => {
        this.files = updatedFiles;
      }
    );
  }

  togglePermissionUploadFiles(): void {
    if (!this.authenticationData.session.permissions.can_upload_files) {
      this.utilsService.runAdminOperation("enable_user_permission_file_upload", {}, false).subscribe({
        next: (_) => {
          this.authenticationData.session.permissions.can_upload_files = true;
          this.permissionStatus = true;
        },
        error: (_) => {
          this.authenticationData.session.permissions.can_upload_files = false;
          this.togglePermissionUploadFiles();
          this.permissionStatus = false;
        }
      });
    } else {
      this.utilsService.runAdminOperation("disable_user_permission_file_upload", {}, false).subscribe(
        () => {
          this.authenticationData.session.permissions.can_upload_files = false;
          this.permissionStatus = false;
        }
      );
    }
  }
}
