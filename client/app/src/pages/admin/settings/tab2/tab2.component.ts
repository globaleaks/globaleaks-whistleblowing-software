import {Component, ElementRef, OnInit, inject, input, viewChild} from "@angular/core";
import {NgForm} from "@angular/forms";
import type {FlowFile} from "@flowjs/flow.js";
import {FlowConfig} from "@flowjs/ngx-flow";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {UtilsService} from "@app/shared/services/utils.service";
import {AppConfigService} from "@app/services/root/app-config.service";
import {preferenceResolverModel} from "@app/models/resolvers/preference-resolver-model";
import {AdminFile} from "@app/models/component-model/admin-file";
import {AdminFileComponent} from "@app/shared/partials/admin-file/admin-file.component";
import {SwitchComponent} from "@app/shared/components/switch/switch.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";
import {OrderByPipe} from "@app/shared/pipes/order-by.pipe";
import {TranslateModule} from "@ngx-translate/core";
import {NgbTooltipModule} from "@ng-bootstrap/ng-bootstrap";

@Component({
    selector: "src-tab2",
    templateUrl: "./tab2.component.html",
    standalone: true,
    imports: [NgbTooltipModule, AdminFileComponent, SwitchComponent, TranslatorPipe, OrderByPipe, TranslateModule]
})
export class Tab2Component implements OnInit {
  private appConfigService = inject(AppConfigService);
  private preferenceResolver = inject(PreferenceResolver);
  private utilsService = inject(UtilsService);
  private nodeResolver = inject(NodeResolver);
  private authenticationService = inject(AuthenticationService);

  readonly contentForm = input<NgForm>();
  readonly flowAdvanced = viewChild<FlowConfig>("flowAdvanced");
  readonly uploaderInput = viewChild<ElementRef>("uploader");

  files: FlowFile[] = [];
  files_names: string[] = [];
  special_files_names = ['css', 'favicon', 'logo', 'script'];
  flow: FlowConfig;
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
      const flowJsInstance = this.utilsService.getFlowInstance({
        target: "api/admin/files/custom",
        allowDuplicateUploads: true,
        singleFile: true,
        query: {fileSizeLimit: this.nodeResolver.dataModel.maximum_filesize * 1024 * 1024}
      });

      flowJsInstance.on("fileSuccess", (_) => {
        this.appConfigService.reinit(false);
        this.updateFiles();
      });

      flowJsInstance.on("fileError", (_) => {
        const uploaderInput = this.uploaderInput();
        if (uploaderInput) {
          uploaderInput.nativeElement.value = "";
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
      }
    );
  }

  updateFiles = (): void => {
    this.utilsService.getFiles().subscribe(
      (updatedFiles) => {
        this.files = updatedFiles;
	this.files_names.splice(0, this.files_names.length);
	this.files.forEach(file => {
          this.files_names.push(file.name);
	});
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
