import {EventEmitter, Injectable, Renderer2} from "@angular/core";
import * as Flow from "@flowjs/flow.js";
import {TranslateService} from "@ngx-translate/core";
import {ActivatedRoute, Router} from "@angular/router";
import {NgbModal} from "@ng-bootstrap/ng-bootstrap";
import {RequestSupportComponent} from "@app/shared/modals/request-support/request-support.component";
import {HttpService} from "@app/shared/services/http.service";
import {TokenResource} from "@app/shared/services/token-resource.service";
import {HttpClient, HttpHeaders} from "@angular/common/http";
import {Observable, from, map, switchMap} from "rxjs";
import {ConfirmationWithPasswordComponent} from "@app/shared/modals/confirmation-with-password/confirmation-with-password.component";
import {ConfirmationWith2faComponent} from "@app/shared/modals/confirmation-with2fa/confirmation-with2fa.component";
import {PreferenceResolver} from "@app/shared/resolvers/preference.resolver";
import {DeleteConfirmationComponent} from "@app/shared/modals/delete-confirmation/delete-confirmation.component";
import {ClipboardService} from "ngx-clipboard";
import {TlsConfig} from "@app/models/component-model/tls-confiq";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {NewUser} from "@app/models/admin/new-user";
import {userResolverModel} from "@app/models/resolvers/user-resolver-model";
import {NewContext} from "@app/models/admin/new-context";
import {contextResolverModel} from "@app/models/resolvers/context-resolver-model";
import {notificationResolverModel} from "@app/models/resolvers/notification-resolver-model";
import {questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import {Field} from "@app/models/resolvers/field-template-model";
import {rtipResolverModel} from "@app/models/resolvers/rtips-resolver-model";
import {Option} from "@app/models/whistleblower/wb-tip-data";
import {Status} from "@app/models/app/public-model";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {FlowFile} from "@flowjs/flow.js";
import {AcceptAgreementComponent} from "@app/shared/modals/accept-agreement/accept-agreement.component";
import {RFile, WbFile} from "@app/models/app/shared-public-model";
import {FileViewComponent} from "@app/shared/modals/file-view/file-view.component";
import {CryptoService} from "@app/shared/services/crypto.service";
import { DownloadConfirmationComponent } from "../modals/download-confirmation/download-confirmation.component";
import { AccreditationSubscriberModel } from "@app/models/resolvers/accreditation-model";
import { FileItem } from "@app/models/reciever/sendtip-data";
@Injectable({
  providedIn: "root"
})
export class UtilsService {
  supportedViewTypes = ["application/pdf", "audio/mpeg", "image/gif", "image/jpeg", "image/png", "text/csv", "text/plain", "video/mp4"];

  constructor(private authenticationService: AuthenticationService,private activatedRoute: ActivatedRoute,protected appDataService: AppDataService,private cryptoService: CryptoService, private tokenResource: TokenResource,private translateService: TranslateService, private clipboardService: ClipboardService, private http: HttpClient, private httpService: HttpService, private modalService: NgbModal, private preferenceResolver: PreferenceResolver, private router: Router) {
  }

  updateNode(nodeResolverModel:nodeResolverModel) {
    this.httpService.updateNodeResource(nodeResolverModel).subscribe();
  }

  routeGuardRedirect(route="login", skipChange = false){
    const loginUrlWithParam = `/${route}?redirect=${encodeURIComponent(location.hash.substring(1))}`;
    this.router.navigateByUrl(loginUrlWithParam, { skipLocationChange: skipChange }).then(() => {});
  }

  newItemOrder(objects: any[], key: string): number {
    if (objects.length === 0) {
      return 0;
    }

    let max = 0;
    objects.forEach(object => {
      if (object[key] > max) {
        max = object[key];
      }
    });

    return max + 1;
  }

  rolel10n(role: string) {
    let ret = "";

    if (role) {
      ret = role === "receiver" ? "recipient" : role;
      ret = ret.charAt(0).toUpperCase() + ret.slice(1);
    }

    return ret;
  }

  download(url: string): Observable<void> {
    return from(this.tokenResource.getWithProofOfWork()).pipe(
      switchMap((token: any) => {
        window.open(`${url}?token=${token.id}:${token.answer}`);
        return new Observable<void>((observer) => {
          observer.complete();
        });
      })
    );
  }

  isUploading(uploads?: any) {
    if (uploads) {
      for (const key in uploads) {
        if (uploads[key].flowFile && uploads[key].flowFile.isUploading()) {
          return true;
        }
      }
    }
    return false;
  }

  removeStyles(renderer: Renderer2, document:Document, link:string){
    const defaultBootstrapLink = document.head.querySelector(`link[href="${link}"]`);
    if (defaultBootstrapLink) {
      renderer.removeChild(document.head, defaultBootstrapLink);
    }
  }


  resumeFileUploads(uploads: any) {
    if (uploads) {
      for (const key in uploads) {
        if (uploads[key] && uploads[key].flowJs) {
          uploads[key].flowJs.upload();
        }
      }
    }
  }

  getDirection(language: string): string {
    const rtlLanguages = ["ar", "dv", "fa", "fa_AF", "he", "ps", "ug", "ur"];
    return rtlLanguages.includes(language) ? "rtl" : "ltr";
  }

  view(authenticationService: AuthenticationService, url: string, _: string, callback: (blob: Blob) => void): void {
    const headers = new HttpHeaders({
      "x-session": authenticationService.session.id
    });

    this.http.get(url, {
      headers: headers,
      responseType: "blob"
    }).subscribe(
      (response: Blob) => {
        callback(response);
      }
    );
  }

  getCardSize(num: number) {
    if (num < 2) {
      return "col-md-12";
    } else if (num === 2) {
      return "col-md-6";
    } else if (num === 3) {
      return "col-md-4";
    } else {
      return "col-md-3 col-sm-6";
    }
  }

  scrollToTop() {
    document.documentElement.scrollTop = 0;
  }

  reloadCurrentRoute() {
    const currentUrl = this.router.url;
    this.router.navigateByUrl("blank", {skipLocationChange: true, replaceUrl: true}).then(() => {
      this.router.navigate([currentUrl]).then();
    });
  }

  reloadComponent() {
    this.router.routeReuseStrategy.shouldReuseRoute = function () {
      return false;
    };

    const currentUrl = this.router.url + "?";

    this.router.navigateByUrl(currentUrl)
      .then(() => {
        this.router.navigated = false;
        this.router.navigate([this.router.url]).then();
      });
  }

  onFlowUpload(flowJsInstance:Flow, file:File){
    const fileNameParts = file.name.split(".");
    const fileExtension = fileNameParts.pop();
    const fileNameWithoutExtension = fileNameParts.join(".");
    
    const fileNameWithTimestamp = `${fileNameWithoutExtension}.${fileExtension}`;
    const modifiedFile = new File([file], fileNameWithTimestamp, {type: file.type});

    flowJsInstance.addFile(modifiedFile);
    flowJsInstance.upload();
  }

  swap($event: Event, index: number, n: number, questionnaire:questionnaireResolverModel): void {
    $event.stopPropagation();

    const target = index + n;
    if (target < 0 || target >= questionnaire.steps.length) {
      return;
    }

    [questionnaire.steps[index], questionnaire.steps[target]] =
      [questionnaire.steps[target], questionnaire.steps[index]];

    this.http.put("api/admin/steps", {
      operation: "order_elements",
      args: {
        ids: questionnaire.steps.map((c: { id: string; }) => c.id),
        questionnaire_id: questionnaire.id
      },
    }).subscribe();
  }

  toggleCfg(authenticationService: AuthenticationService, tlsConfig:TlsConfig, dataToParent:EventEmitter<string>) {
    if (tlsConfig.enabled) {
      const authHeader = authenticationService.getHeader();
      this.httpService.disableTLSConfig(tlsConfig, authHeader).subscribe(() => {
        dataToParent.emit();
      });
    } else {
      const authHeader = authenticationService.getHeader();
      this.httpService.enableTLSConfig(tlsConfig, authHeader).subscribe(() => {
        window.location.href = "https://" + window.location.hostname + "/#/login";
      });
    }
  }

  reloadCurrentRouteFresh(removeQueryParam = false) {

    let currentUrl = this.router.url;
    if (removeQueryParam) {
      currentUrl = this.router.url.split("?")[0];
    }

    this.router.navigateByUrl("/blank", {skipLocationChange: true}).then(() => {
      this.router.navigateByUrl(currentUrl, {replaceUrl: true}).then();
    });
  }

  showWBLoginBox() {
    return this.router.url === "/submission";
  }

  showUserStatusBox(authenticationService: AuthenticationService, appDataService: AppDataService) {
    return appDataService.page === "accreditation-request" || (appDataService.public.node.wizard_done &&
        appDataService.page !== "homepage" &&
        appDataService.page !== "submissionpage" &&
        authenticationService.session);
  }

  isWhistleblowerPage(authenticationService: AuthenticationService, appDataService: AppDataService) {
    const currentUrl = this.router.url;
    return appDataService.public.node.wizard_done && (!authenticationService.session || (location.hash==="#/" || location.hash.startsWith("#/submission"))) && ((currentUrl === "/" && !appDataService.public.node.enable_signup) || currentUrl === "/submission" || currentUrl === "/blank");
  }

  stopPropagation(event: Event) {
    event.stopPropagation();
  }

  encodeString(string: string): string {
    const codeUnits = Uint16Array.from(
      {length: string.length},
      (_, index) => string.charCodeAt(index)
    );

    const charCodes = new Uint8Array(codeUnits.buffer);

    let result = "";
    charCodes.forEach((char) => {
      result += String.fromCharCode(char);
    });

    return btoa(result);
  }

  openSupportModal(appDataService: AppDataService) {
    if (appDataService.public.node.custom_support_url) {
      window.open(appDataService.public.node.custom_support_url, "_blank");
    } else {
      this.modalService.open(RequestSupportComponent,{backdrop: "static",keyboard: false});
    }
  }

  array_to_map(receivers: any) {
    const ret: any = {};

    receivers.forEach(function (element: any) {
      ret[element.id] = element;
    });

    return ret;
  }

  copyToClipboard(data: string) {
    this.clipboardService.copyFromContent(data);
  }

  getSubmissionStatusText(status: string,substatus:string, submission_statuses: Status[]) {
    let text;
    for (let i = 0; i < submission_statuses.length; i++) {
      if (submission_statuses[i].id === status) {
        text = this.translateService.instant(submission_statuses[i].label);

        const subStatus = submission_statuses[i].substatuses;
        for (let j = 0; j < subStatus.length; j++) {
          if (subStatus[j].id === substatus && subStatus[j].label) {
            text += ' \u2013 ' + subStatus[j].label;
            break;
          }
        }
        break;
      }
    }
    return text?text:"";
  }

  searchInObject(obj: any, searchTerm: string) {
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        const value = obj[key];

        if (typeof value === 'string' && value.toLowerCase().includes(searchTerm.toLowerCase())) {
          return true;
        } else if (typeof value === 'object') {
          if (this.searchInObject(value, searchTerm)) {
            return true;
          }
        }
      }
    }
    return false;
  }

  isDatePassed(time: string) {
    const report_date = new Date(time);
    const current_date = new Date();
    return current_date > report_date;
  }

  isNever(time: string) {
    const date = new Date(time);
    return date.getTime() >= 32503680000000;
  }

  deleteFromList(list:  { [key: string]: Field}[], elem: { [key: string]: Field}) {
    const idx = list.indexOf(elem);
    if (idx !== -1) {
      list.splice(idx, 1);
    }
  }

  submitSupportRequest(arg: {mail_address: string,text: string} ) {
    const param = JSON.stringify({
      "mail_address": arg.mail_address,
      "text": arg.text,
      "url": window.location.href.replace("localhost", "127.0.0.1")
    });
    this.httpService.requestSupport(param).subscribe();
  }

  submitAccreditationRequest(request: AccreditationSubscriberModel){
    return this.httpService.requestAccreditationEO(request);
  }

  submitAccreditationRequestFromInvitation(uuid: string, request: AccreditationSubscriberModel){
    return this.httpService.requestAccreditationFromInviteEO(uuid, request);
  }

  runUserOperation(operation: string, args: any, refresh: boolean) {
    return this.httpService.runOperation("api/user/operations", operation, args, refresh);
  }

  runRecipientOperation(operation: string, args: {rtips:string[], receiver?: {id: number}}, refresh: boolean) {
    return this.httpService.runOperation("api/recipient/operations", operation, args, refresh);
  }

  go(path: string): void {
    this.router.navigateByUrl(path).then();
  }

  maskScore(score: number, translateService: TranslateService) {
    if (score === 1) {
      return translateService.instant("Low");
    } else if (score === 2) {
      return translateService.instant("Medium");
    } else if (score === 3) {
      return translateService.instant("High");
    } else {
      return translateService.instant("None");
    }
  }

  getStaticFilter(data: any[], model:{id: number;label: string;}[], key: string, translateService: TranslateService): any[] {
    if (model.length === 0) {
      return data;
    } else {
      const rows: any[] = [];
      data.forEach(data_row => {
        model.forEach(selected_option => {
          if (key === "score") {
            const scoreLabel = this.maskScore(data_row[key], translateService);
            if (scoreLabel === selected_option.label) {
              rows.push(data_row);
            }
          } else {
            if (data_row[key] === selected_option.label) {
              rows.push(data_row);
            }
          }
        });
      });
      return rows;
    }
  }

  getDateFilter(Tips: rtipResolverModel[], report_date_filter:[number, number] | null, update_date_filter: [number, number] | null, expiry_date_filter: [number, number] | null): rtipResolverModel[] {
    const filteredTips: rtipResolverModel[] = [];
    Tips.forEach(rows => {
      const m_row_rdate = new Date(rows.last_access).getTime();
      const m_row_udate = new Date(rows.update_date).getTime();
      const m_row_edate = new Date(rows.expiration_date).getTime();

      if (
        (report_date_filter === null || (report_date_filter[0] === 0 || (m_row_rdate > report_date_filter[0] && m_row_rdate < report_date_filter[1]))) &&
        (update_date_filter === null || (update_date_filter[0] === 0 || (m_row_udate > update_date_filter[0] && m_row_udate < update_date_filter[1]))) &&
        (expiry_date_filter === null || (expiry_date_filter[0] === 0 || (m_row_edate > expiry_date_filter[0] && m_row_edate < expiry_date_filter[1])))
      ) {
        filteredTips.push(rows);
      }
    });

    return filteredTips;
  }

  print() {
    window.print();
  }

  saveAs(authenticationService: AuthenticationService, filename: any, url: string): void {

    const headers = new HttpHeaders({
      "X-Session": authenticationService.session.id
    });

    this.http.get(url, {responseType: "blob", headers: headers}).subscribe(
      response => {
        this.saveBlobAs(filename, response);
      }
    );
  }


  saveBlobAs(filename:string,response:Blob){
    const blob = new Blob([response], {type: "text/plain;charset=utf-8"});
    const blobUrl = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename;
    a.click();

    setTimeout(() => {
      URL.revokeObjectURL(blobUrl);
    }, 1000);
  }

  
  getPostponeDate(ttl: number): Date {
    const date = new Date();
    date.setDate(date.getDate() + ttl + 1);
    date.setUTCHours(0, 0, 0, 0);
    return date;
  }

  update(node: nodeResolverModel) {
    return this.httpService.requestUpdateAdminNodeResource(node);
  }

  AdminL10NResource(lang: string) {
    return this.httpService.requestAdminL10NResource(lang);
  }

  updateAdminL10NResource(data: {[key: string]: string}, lang: string) {
    return this.httpService.requestUpdateAdminL10NResource(data, lang);
  }

  DefaultL10NResource(lang: string) {
    return this.httpService.requestDefaultL10NResource(lang);
  }

  runAdminOperation(operation: string, args: {value: string}|object, refresh: boolean) {
    return this.runOperation("api/admin/config", operation, args, refresh);
  }

  deleteDialog() {
    return this.openConfirmableModalDialogReport("", "").subscribe();
  }


  runOperation(api: string, operation: string, args?: {value: string}|object, refresh?: boolean): Observable<any> {
    const requireConfirmation = [
      "enable_encryption",
      "disable_2fa",
      "get_recovery_key",
      "toggle_escrow",
      "toggle_user_escrow",
      "enable_user_permission_file_upload",
      "reset_submissions"
    ];

    if (!args) {
      args = {};
    }

    if (!refresh) {
      refresh = false;
    }

    if (requireConfirmation.indexOf(operation) !== -1) {
      return new Observable((observer) => {
        this.getConfirmation().subscribe((secret: string) => {
          const headers = new HttpHeaders({"X-Confirmation": this.encodeString(secret)});

          this.http.put(api, {"operation": operation, "args": args}, {headers}).subscribe(  {
              next: (response) => {
                if (refresh) {
                  this.reloadComponent();
                }
                observer.next(response)
              },
              error: (error) => {
                observer.error(error);
              }
            }
          )
        });
      });
    } else {
      return this.http.put(api, {"operation": operation, "args": args}).pipe(
        map((response) => {
          if (refresh) {
            this.reloadComponent();
          }
          return response;
        })
      );
    }
  }

  getConfirmation(): Observable<string> {
    return new Observable((observer) => {
      let modalRef;

      if (this.preferenceResolver.dataModel.two_factor) {
        modalRef = this.modalService.open(ConfirmationWith2faComponent,{backdrop: "static",keyboard: false});
      } else {
        modalRef = this.modalService.open(ConfirmationWithPasswordComponent,{backdrop: "static",keyboard: false});
      }

      modalRef.componentInstance.confirmFunction = (secret: string) => {
        observer.next(secret);
        observer.complete();
      };
    });
  }

  openConfirmableModalDialogReport(arg: string, scope: any): Observable<string> {
    scope = !scope ? this : scope;
    return new Observable((observer) => {
      const modalRef = this.modalService.open(DeleteConfirmationComponent,{backdrop: "static",keyboard: false});
      modalRef.componentInstance.arg = arg;
      modalRef.componentInstance.scope = scope;
      modalRef.componentInstance.confirmFunction = () => {
        observer.complete()
        this.openPasswordConfirmableDialog(arg, scope);
      };
    });
  }

  openPasswordConfirmableDialog(arg: string, scope: any){
    return this.runAdminOperation("reset_submissions", {}, true).subscribe({
      next: (_) => {
      },
      error: (_) => {
        this.openPasswordConfirmableDialog(arg, scope)
      }
    });
  }

  getFiles(): Observable<FlowFile[]> {
    return this.http.get<FlowFile[]>("api/admin/files");
  }

  deleteFile(url: string): Observable<void> {
    return this.http.delete<void>(url);
  }

  deleteAdminUser(user_id: string) {
    return this.httpService.requestDeleteAdminUser(user_id);
  }

  deleteAdminContext(user_id: string) {
    return this.httpService.requestDeleteAdminContext(user_id);
  }

  deleteStatus(url: string) {
    return this.httpService.requestDeleteStatus(url);
  }

  deleteSubStatus(url: string) {
    return this.httpService.requestDeleteStatus(url);
  }

  addAdminUser(user: NewUser) {
    return this.httpService.requestAddAdminUser(user);
  }

  updateAdminUser(id: string, user: userResolverModel) {
    return this.httpService.requestUpdateAdminUser(id, user);
  }

  addAdminContext(context: NewContext) {
    return this.httpService.requestAddAdminContext(context);
  }

  updateAdminContext(context: contextResolverModel, id: string) {
    return this.httpService.requestUpdateAdminContext(context, id);
  }

  updateAdminNotification(notification: notificationResolverModel) {
    return this.httpService.requestUpdateAdminNotification(notification);
  }

  readFileAsText(file: File): Observable<string> {
    return new Observable<string>((observer) => {
      const reader = new FileReader();

      reader.onload = (event) => {
        if (event.target) {
          observer.next(event.target.result as string);
          observer.complete();
        } else {
          observer.error(new Error("Event target is null."));
        }
      };

      reader.onerror = (error) => {
        observer.error(error);
      };

      reader.readAsText(file);
    });
  }

  moveUp(elem: any): void {
    elem[this.getYOrderProperty(elem)] -= 1;
  }

  moveDown(elem: any): void {
    elem[this.getYOrderProperty(elem)] += 1;
  }

  moveLeft(elem: any): void {
    elem[this.getXOrderProperty(elem)] -= 1;
  }

  moveRight(elem: any): void {
    elem[this.getXOrderProperty(elem)] += 1;
  }

  getXOrderProperty(_: Option[]): string {
    return "x";
  }

  getYOrderProperty(elem: Option): keyof Option {
    return ("order" in elem ? "order" : "y") as keyof Option;
  }

  assignUniqueOrderIndex(elements: Option[]): void {
    if (elements.length <= 0) {
        return;
    }

    const key: keyof Option = this.getYOrderProperty(elements[0]) as keyof Option;
    if (elements.length) {
        let i = 0;
        elements = elements.sort((a, b) => (a[key] as number) - (b[key] as number));
        elements.forEach((element) => {
            (element[key] as number) = i;
            i += 1;
        });
    }
  }

  deleteResource( list: any[], res: any): void {
      list.splice(list.indexOf(res), 1);
  }

  acceptPrivacyPolicyDialog(): Observable<string> {
    return new Observable((observer) => {
      const modalRef = this.modalService.open(AcceptAgreementComponent, {
        backdrop: 'static',
        keyboard: false,
      });
      modalRef.componentInstance.confirmFunction = () => {
        observer.complete()
        return this.http.put("api/user/operations", {
          operation: "accepted_privacy_policy",
          args: {}
        }).subscribe(() => {
          this.preferenceResolver.dataModel.accepted_privacy_policy = "";
          modalRef.close();
        });
      };
    });
  }
  generateCSV(dataString: string, fileName: string, headerx: string[]): void {
    const data = JSON.parse(dataString);

    if (!Array.isArray(data)) {
      console.error('Invalid data format');
      return;
    }

    const headers = Object.keys(data[0] || {});
    const newHeader = headerx.join(',');
    const csvContent = `${newHeader ? `${newHeader}\n` : ""}${data.map(row => headers.map(header => row[header]).join(',')).join('\n')}`;

    if (!csvContent.trim()) {
      console.warn('No data to export');
      return;
    }

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const link = document.createElement('a');
    link.href = window.URL.createObjectURL(blob);
    link.download = `${fileName}.csv`;
    link.click();
  }

  public viewRFile(file: WbFile) {
    const modalRef = this.modalService.open(FileViewComponent, {backdrop: 'static', keyboard: false});
    modalRef.componentInstance.args = {
      file: file,
      loaded: false,
      iframeHeight: window.innerHeight * 0.75
    };
  }

  public viewWBFile(file: RFile) {
    const modalWBRef = this.modalService.open(FileViewComponent, {backdrop: 'static', keyboard: false});
    modalWBRef.componentInstance.args = {
      file: file,
      loaded: false,
      iframeHeight: window.innerHeight * 0.75
    };
  }

  public downloadRFile(wbFile: WbFile) {

    if(wbFile.status === "VERIFIED"){
    const param = JSON.stringify({});
      this.httpService.requestToken(param).subscribe(
      {
        next: async token => {
          this.cryptoService.proofOfWork(token.id).subscribe(
              (ans) => {
               const url = this.authenticationService.session.role === "whistleblower"?"api/whistleblower/wbtip/wbfiles/":"api/recipient/wbfiles/";
                  window.open(url + wbFile.id + "?token=" + token.id + ":" + ans);
                this.appDataService.updateShowLoadingPanel(false);
              }
          );
        }
      }
    );

      return null ;
    }
    else{
      const url = this.authenticationService.session.role === "whistleblower"?"api/whistleblower/wbtip/wbfiles/":"api/recipient/wbfiles/";
      return this.showAlertFileModal(wbFile, url+ wbFile.id )
    }

  }



  flowDefault = new Flow({
    testChunks: false,
    permanentErrors:[500, 501],
    speedSmoothingFactor:0.01,
    allowDuplicateUploads:false,
    singleFile:false,
    generateUniqueIdentifier:() => {
      return crypto.randomUUID();
    },
    headers:() => {
      return this.authenticationService.getHeader();
    }
  });


  sumDaysToDate(date: string, daysNum: number): Date{

    let first_date = new Date(date);

    let final_date = new Date();
    final_date.setDate(first_date.getDate() + daysNum);

    return final_date;

  }


  public downloadWBFile(wbFile: RFile) {

    const param = JSON.stringify({});
    this.httpService.requestToken(param).subscribe(
      {
        next: async token => {
          this.cryptoService.proofOfWork(token.id).subscribe(
            (ans) => {
              if (this.authenticationService.session.role === "receiver") {
                window.open("api/recipient/rfiles/" + wbFile.id + "?token=" + token.id + ":" + ans);
              } else {
                window.open("api/whistleblower/wbtip/rfiles/" + wbFile.id + "?token=" + token.id + ":" + ans);
              }
              this.appDataService.updateShowLoadingPanel(false);
            }
          );
        }
      }
    );
  }

  private showAlertFileModal(wbFile: any, url: string){
    const modalRef = this.modalService.open(DownloadConfirmationComponent, {backdrop: 'static', keyboard: false});
      modalRef.componentInstance.arg = JSON.stringify({});
      modalRef.componentInstance.text = wbFile.status==="PENDING" ? "The selected file is not verified. Proceed anyway with the download?" : "The selected file is infected. Proceed anyway with the download?" ;
      modalRef.componentInstance.confirmFunction = (arg: string) => {
        this.httpService.requestToken(arg).subscribe(
        {
          next: async token => {
            this.cryptoService.proofOfWork(token.id).subscribe(
              (ans) => {
                  window.open(url + "?token=" + token.id + ":" + ans);
                  this.appDataService.updateShowLoadingPanel(false);
              }
            );
          }
        }
      )
      };
      return modalRef.result;
  }


  public downloadGenericFile(file: FileItem) {

    if(file.status === "VERIFIED"){

      const param = JSON.stringify({});
      this.httpService.requestToken(param).subscribe(
        {
          next: async token => {
            this.cryptoService.proofOfWork(token.id).subscribe(
              (ans) => {
                window.open(file.download_url + "?token=" + token.id + ":" + ans);
                this.appDataService.updateShowLoadingPanel(false);
              }
            );
          }
        }
      );
      return null;
    }
    else{
      return this.showAlertFileModal(file, file.download_url ? file.download_url : '');
    }
  }



  getCookie(name: string) {
    let ca: Array<string> = document.cookie.split(';');
    let caLen: number = ca.length;
    let cookieName = `${name}=`;
    let c: string;

    for (let i: number = 0; i < caLen; i += 1) {
        c = ca[i].replace(/^\s+/g, '');
        if (c.startsWith(cookieName)) {
            return c.substring(cookieName.length, c.length);
        }
    }
    return null;
  }

}
