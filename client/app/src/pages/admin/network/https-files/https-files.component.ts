import {Component, ElementRef, OnInit, inject, input, viewChild, output} from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {ConfirmationComponent} from "@app/shared/modals/confirmation/confirmation.component";
import {NodeResolver} from "@app/shared/resolvers/node.resolver";
import {HttpService} from "@app/shared/services/http.service";
import {UtilsService} from "@app/shared/services/utils.service";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {TlsConfig} from "@app/models/component-model/tls-confiq";
import {FileResource, FileResources} from "@app/models/component-model/file-resources";
import {DatePipe} from "@angular/common";
import {HttpsCsrGenComponent} from "../https-csr-gen/https-csr-gen.component";
import {TranslatorPipe} from "@app/shared/pipes/translate";

@Component({
    selector: "src-https-files",
    templateUrl: "./https-files.component.html",
    standalone: true,
    imports: [HttpsCsrGenComponent, DatePipe, TranslatorPipe]
})
export class HttpsFilesComponent implements OnInit {
  private authenticationService = inject(AuthenticationService);
  private nodeResolver = inject(NodeResolver);
  private httpService = inject(HttpService);
  private modalService = inject(NgbModal);
  private utilsService = inject(UtilsService);

  readonly updated = output<void>();
  readonly tlsConfig = input.required<TlsConfig>();
  readonly state = input(0);
  readonly pkInput = viewChild<ElementRef<HTMLInputElement>>('pkInput');
  readonly certificateInput = viewChild<ElementRef<HTMLInputElement>>('certificateInput');
  readonly iCertificateInput = viewChild<ElementRef<HTMLInputElement>>('iCertificateInput');

  nodeData: nodeResolverModel;
  fileResources: FileResources = {
    key: {name: "key"},
    cert: {name: "cert"},
    chain: {name: "chain"},
    csr: {name: "csr"},
  };
  csr_state = {
    open: false
  };

  ngOnInit(): void {
    this.nodeData = this.nodeResolver.dataModel;
  }

  postFile(files: FileList | null, resource: FileResource) {
    if (files && files.length > 0) {
      const file = files[0];
      this.utilsService.readFileAsText(file).subscribe(
        (str: string) => {
          resource.content = str;
          this.httpService.requestCSRContentResource(resource.name, resource).subscribe({
           next:() => {
              this.updated.emit();
            },
           error:()=> {
              this.clearInputFields();
            }
          });
        },
      );
    }
  }

  genKey() {
    const authHeader = this.authenticationService.getHeader();
    this.httpService.requestUpdateTlsConfigFilesResource("key", authHeader, this.fileResources.key).subscribe(() => {
      this.updated.emit();
    });
  }

  deleteFile(fileResource: FileResource) {
    const modalRef = this.modalService.open(ConfirmationComponent, {backdrop: 'static', keyboard: false, ariaLabelledBy: 'modal-title'});
    modalRef.componentInstance.arg = fileResource.name;
    modalRef.componentInstance.confirmFunction = (arg: string) => {
      return this.httpService.requestDeleteTlsConfigFilesResource(arg).subscribe(() => {
        this.clearInputFields();
        this.updated.emit();
      });
    };
    return modalRef.result;
  }

  clearInputFields(){
    const pkInput = this.pkInput();
    if (pkInput) {
      pkInput.nativeElement.value = "";
    }
    const certificateInput = this.certificateInput();
    if (certificateInput) {
      certificateInput.nativeElement.value = "";
    }
    const iCertificateInput = this.iCertificateInput();
    if (iCertificateInput) {
      iCertificateInput.nativeElement.value = "";
    }
  }

  downloadCSR() {
    this.httpService.downloadCSRFile().subscribe(
      (response: Blob) => {
        const blob = new Blob([response], {type: "application/octet-stream"});
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "csr.pem";
        link.click();
        window.URL.revokeObjectURL(url);
      },
    );
  }

  toggleCfg() {
    this.utilsService.toggleCfg(this.authenticationService, this.tlsConfig(), this.updated);
  }

  resetCfg() {
    const modalRef = this.modalService.open(ConfirmationComponent, {backdrop: 'static', keyboard: false, ariaLabelledBy: 'modal-title'});
    modalRef.componentInstance.arg = null;
    modalRef.componentInstance.confirmFunction = () => {
      return this.httpService.requestDeleteTlsConfigResource().subscribe(() => {
        this.updated.emit();
      });
    };
    return modalRef.result;
  }

  isCsrSet(): boolean {
    return !!this.tlsConfig().files.csr?.set;
  }
}