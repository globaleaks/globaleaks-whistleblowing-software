import {Injectable} from "@angular/core";
import {HttpClient, HttpHeaders, HttpResponse} from "@angular/common/http";
import {Observable} from "rxjs";
import {PasswordRecoveryResponseModel} from "@app/models/authentication/password-recovery-response-model";
import {Router} from "@angular/router";
import {tenantResolverModel} from "@app/models/resolvers/tenant-resolver-model";
import {nodeResolverModel} from "@app/models/resolvers/node-resolver-model";
import {networkResolverModel} from "@app/models/resolvers/network-resolver-model";
import {FileResource} from "@app/models/component-model/file-resources";
import {TlsConfig} from "@app/models/component-model/tls-confiq";
import {Answers} from "@app/models/reciever/reciever-tip-data";
import {NewQuestionare} from "@app/models/admin/new-questionare";
import {Step, questionnaireResolverModel} from "@app/models/resolvers/questionnaire-model";
import {NewUser} from "@app/models/admin/new-user";
import {userResolverModel} from "@app/models/resolvers/user-resolver-model";
import {NewContext} from "@app/models/admin/new-context";
import {NewStep} from "@app/models/admin/new-step";
import {NewField} from "@app/models/admin/new-field";
import {FieldTemplate} from "@app/models/admin/field-Template";
import {Field, fieldtemplatesResolverModel} from "@app/models/resolvers/field-template-model";
import {contextResolverModel} from "@app/models/resolvers/context-resolver-model";
import {Root, Status, Substatus} from "@app/models/app/public-model";
import {notificationResolverModel} from "@app/models/resolvers/notification-resolver-model";
import {Session, SessionRefresh} from "@app/models/authentication/session";
import {RFile, Comment} from "@app/models/app/shared-public-model";
import {preferenceResolverModel} from "@app/models/resolvers/preference-resolver-model";
import {TokenResponse} from "@app/models/authentication/token-response";
import {tipsResolverModel} from "@app/models/resolvers/tips-resolver-model";
import {redirectResolverModel} from "@app/models/resolvers/redirect-resolver-model";
import {WbTipData} from "@app/models/whistleblower/wb-tip-data";
import {auditlogResolverModel} from "@app/models/resolvers/auditlog-resolver-model";
import {jobResolverModel} from "@app/models/resolvers/job-resolver-model";
import {rtipResolverModel} from "@app/models/resolvers/rtips-resolver-model";
import {IarData} from "@app/models/reciever/Iar-data";
import {statusResolverModel} from "@app/models/resolvers/status-resolver-model";
import {statisticsResolverModel} from "@app/models/resolvers/statistics-resolver-model";
import { RedactionData } from "@app/models/component-model/redaction";
import { AccreditationSubscriberModel } from "@app/models/resolvers/accreditation-model";
import { AccreditationRequestModel, EOExtendedInfo, EOInfo, ExternalOrganization } from "@app/models/accreditor/organization-data";


@Injectable({
  providedIn: "root"
})
export class HttpService {

  constructor(private httpClient: HttpClient, private router: Router) {
  }

  getPublicResource(): Observable<HttpResponse<Root>> {
    return this.httpClient.get<Root>("api/public", {observe: "response"});
  }

  requestAuthTokenLogin(param: string): Observable<Session> {
    return this.httpClient.post<Session>("api/auth/tokenauth", param);
  }

  requestGeneralLogin(param: string): Observable<Session> {
    return this.httpClient.post<Session>("api/auth/authentication", param);
  }

  requestWhistleBlowerLogin(param: string, header: HttpHeaders): Observable<Session> {
    return this.httpClient.post<Session>("api/auth/receiptauth", param, {headers: header});
  }

  requestRefreshUserSession(param: SessionRefresh): Observable<Session> {
    return this.httpClient.post<Session>("api/auth/session", param);
  }

  requestDeleteUserSession(): Observable<Session> {
    return this.httpClient.delete<Session>("api/auth/session");
  }

  requestDeleteTenant(url: string): Observable<tenantResolverModel> {
    return this.httpClient.delete<tenantResolverModel>(url);
  }

  requestUpdateTenant(url: string, data: tenantResolverModel): Observable<tenantResolverModel> {
    return this.httpClient.put<tenantResolverModel>(url, data);
  }

  authorizeIdentity(url: string, data: { reply: string, reply_motivation: string }): Observable<{
    reply: string,
    reply_motivation: string
  }> {
    return this.httpClient.put<{ reply: string, reply_motivation: string }>(url, data);
  }

  deleteDBFile(id: string): Observable<RFile> {
    return this.httpClient.delete<RFile>("api/recipient/rfiles/" + id);
  }

  requestOperations(data: { operation: string, args: { [key: string]: string } }, header?: HttpHeaders): Observable<{
    operation: string,
    args: { [key: string]: string }
  }> {
    const options = {headers: header};
    return this.httpClient.put<{
      operation: string,
      args: { [key: string]: string }
    }>("api/user/operations", data, options);
  }

  requestOperationsRecovery(data: {
    operation: string,
    args: { [key: string]: string }
  }, confirmation: string): Observable<any> {
    const headers = {"X-Confirmation": confirmation};
    return this.httpClient.put<any>("api/user/operations", data, {headers});
  }

  updatePreferenceResource(data: string): Observable<preferenceResolverModel> {
    return this.httpClient.put<preferenceResolverModel>("api/user/preferences", data);
  }

  requestChangePassword(param: string): Observable<PasswordRecoveryResponseModel> {
    return this.httpClient.put<PasswordRecoveryResponseModel>("api/user/reset/password", param);
  }

  requestToken(param: string): Observable<TokenResponse> {
    return this.httpClient.post<TokenResponse>("api/auth/token", param);
  }

  requestResetLogin(param: string): Observable<void> {
    return this.httpClient.post<void>("api/user/reset/password", param);
  }

  requestSignup(param: string): Observable<void> {
    return this.httpClient.post<void>("api/signup", param);
  }

  requestWizard(param: string): Observable<void> {
    return this.httpClient.post<void>("api/wizard", param);
  }

  requestSignupToken(token: string): Observable<TokenResponse> {
    return this.httpClient.post<TokenResponse>("api/signup/" + token, {});
  }

  requestTenantSwitch(url: string): Observable<{ redirect: string }> {
    return this.httpClient.get<{ redirect: string }>(url);
  }

  requestReportSubmission(param: string): Observable<{ receipt: string }> {
    return this.httpClient.post<{ receipt: string }>("api/whistleblower/submission", param);
  }

  requestSupport(param: string): Observable<void> {
    return this.httpClient.post<void>("api/support", param);
  }

  requestNewComment(param: string): Observable<Comment> {
    return this.httpClient.post<Comment>("api/whistleblower/wbtip/comments", param);
  }

  requestUserPreferenceResource(): Observable<preferenceResolverModel> {
    return this.httpClient.get<preferenceResolverModel>("api/user/preferences");
  }

  requestNodeResource(): Observable<nodeResolverModel> {
    return this.httpClient.get<nodeResolverModel>("api/admin/node");
  }

  updateNodeResource(data: nodeResolverModel): Observable<nodeResolverModel> {
    return this.httpClient.put<nodeResolverModel>("api/admin/node", data);
  }

  requestUsersResource(): Observable<userResolverModel[]> {
    return this.httpClient.get<userResolverModel[]>("api/admin/users");
  }

  requestContextsResource(): Observable<contextResolverModel> {
    return this.httpClient.get<contextResolverModel>("api/admin/contexts");
  }

  requestTenantsResource(): Observable<tenantResolverModel> {
    return this.httpClient.get<tenantResolverModel>("api/admin/tenants");
  }

  requestQuestionnairesResource(): Observable<questionnaireResolverModel[]> {
    return this.httpClient.get<questionnaireResolverModel[]>("api/admin/questionnaires");
  }

  requestTipResource(): Observable<tipsResolverModel> {
    return this.httpClient.get<tipsResolverModel>("api/admin/auditlog/tips");
  }

  requestNotificationsResource(): Observable<notificationResolverModel> {
    return this.httpClient.get<notificationResolverModel>("api/admin/notification");
  }

  requestNetworkResource(): Observable<networkResolverModel> {
    return this.httpClient.get<networkResolverModel>("api/admin/network");
  }

  requestUpdateNetworkResource(param: networkResolverModel): Observable<networkResolverModel> {
    return this.httpClient.put<networkResolverModel>("api/admin/network", param);
  }

  requestTlsConfigResource(): Observable<TlsConfig> {
    return this.httpClient.get<TlsConfig>("api/admin/config/tls");
  }

  requestDeleteTlsConfigResource(): Observable<TlsConfig> {
    return this.httpClient.delete<TlsConfig>("api/admin/config/tls");
  }

  requestRedirectsResource(): Observable<redirectResolverModel[]> {
    return this.httpClient.get<redirectResolverModel[]>("api/admin/redirects");
  }

  requestPostRedirectsResource(param: { path1: string, path2: string }): Observable<redirectResolverModel> {
    return this.httpClient.post<redirectResolverModel>("api/admin/redirects", param);
  }

  requestDeleteRedirectsResource(id: string): Observable<redirectResolverModel> {
    return this.httpClient.delete<redirectResolverModel>("api/admin/redirects/" + id);
  }

  requestUpdateTlsConfigFilesResource(name: string, header: HttpHeaders, data: FileResource): Observable<void> {
    return this.httpClient.put<void>("api/admin/config/tls/files/" + name, data, {headers: header});
  }

  requestDeleteTlsConfigFilesResource(name: string): Observable<void> {
    return this.httpClient.delete<void>("api/admin/config/tls/files/" + name);
  }

  requestAdminAcmeResource(param: object, header: HttpHeaders): Observable<void> {
    return this.httpClient.post<void>("api/admin/config/acme/run", param, {headers: header});
  }

  requestCSRContentResource(name: string, param: FileResource): Observable<void> {
    return this.httpClient.post<void>("api/admin/config/tls/files/" + name, param);
  }

  requestCSRDirectContentResource(param: {
    country: string;
    province: string;
    city: string;
    company: string;
    department: string;
    email: string
  }): Observable<any> {
    return this.httpClient.post("api/admin/config/csr/gen", param);
  }

  downloadCSRFile(): Observable<Blob> {
    const url = "api/admin/config/tls/files/csr";
    return this.httpClient.get(url, {responseType: "blob"});
  }

  disableTLSConfig(tls: TlsConfig, header: HttpHeaders): Observable<TlsConfig> {
    const url = "api/admin/config/tls";
    return this.httpClient.put<TlsConfig>(url, tls, {headers: header});
  }

  enableTLSConfig(tls: TlsConfig, header: HttpHeaders): Observable<TlsConfig> {
    const url = "api/admin/config/tls";
    return this.httpClient.post<TlsConfig>(url, tls, {headers: header});
  }

  whistleBlowerTip(): Observable<WbTipData> {
    return this.httpClient.get<WbTipData>("api/whistleblower/wbtip");
  }

  whistleBlowerTipUpdate(param: { cmd: string, answers: Answers }): Observable<void> {
    return this.httpClient.post<void>("api/whistleblower/wbtip/fillform", param);
  }

  whistleBlowerIdentityUpdate(param: { identity_field_id: string, identity_field_answers: Answers }): Observable<void> {
    return this.httpClient.post<void>("api/whistleblower/wbtip/identity", param);
  }

  requestAdminFieldTemplateResource(): Observable<fieldtemplatesResolverModel[]> {
    return this.httpClient.get<fieldtemplatesResolverModel[]>("api/admin/fieldtemplates");
  }

  requestUpdateAdminNodeResource(data: nodeResolverModel): Observable<nodeResolverModel> {
    return this.httpClient.put<nodeResolverModel>("api/admin/node", data);
  }

  requestAdminL10NResource(lang: string): Observable<{ [key: string]: string }> {
    return this.httpClient.get<{ [key: string]: string }>("api/admin/l10n/" + lang);
  }

  requestUpdateAdminL10NResource(data: { [key: string]: string }, lang: string): Observable<{ [key: string]: string }> {
    return this.httpClient.put<{ [key: string]: string }>("api/admin/l10n/" + lang, data);
  }

  requestDefaultL10NResource(lang: string): Observable<{ [key: string]: string }> {
    return this.httpClient.get<{ [key: string]: string }>("/data/l10n/" + lang + ".json");
  }

  requestAdminAuditLogResource(): Observable<auditlogResolverModel> {
    return this.httpClient.get<auditlogResolverModel>("api/admin/auditlog");
  }

  addQuestionnaire(param: NewQuestionare): Observable<questionnaireResolverModel> {
    return this.httpClient.post<questionnaireResolverModel>("api/admin/questionnaires", param);
  }

  requestDeleteAdminQuestionnaire(id: string): Observable<questionnaireResolverModel> {
    return this.httpClient.delete<questionnaireResolverModel>("api/admin/questionnaires/" + id);
  }

  requestUpdateAdminQuestionnaire(id: string, param: questionnaireResolverModel): Observable<questionnaireResolverModel> {
    return this.httpClient.put<questionnaireResolverModel>("api/admin/questionnaires/" + id, param);
  }

  requestJobResource(): Observable<jobResolverModel> {
    return this.httpClient.get<jobResolverModel>("api/admin/auditlog/jobs");
  }

  receiverTipResource(): Observable<rtipResolverModel[]> {
    return this.httpClient.get<rtipResolverModel[]>("api/recipient/rtips");
  }

  requestStatisticsResource(): Observable<statisticsResolverModel> {
    return this.httpClient.get<statisticsResolverModel>("api/analyst/stats");
  }

  iarResource(): Observable<IarData[]> {
    return this.httpClient.get<IarData[]>("api/custodian/iars");
  }

  receiverTip(id: string | null): Observable<rtipResolverModel[]> {
    return this.httpClient.get<rtipResolverModel[]>("api/recipient/rtips/" + id);
  }

  rTipsRequestNewComment(param: string, id: string): Observable<Comment> {
    return this.httpClient.post<Comment>(`api/recipient/rtips/${id}/comments`, param);
  }

  requestStatusesResource(): Observable<statusResolverModel> {
    return this.httpClient.get<statusResolverModel>("api/admin/statuses");
  }

  addSubmissionStatus(param: { label: string, order: number }): Observable<statusResolverModel> {
    return this.httpClient.post<statusResolverModel>("api/admin/statuses", param);
  }

  fetchTenant(): Observable<tenantResolverModel[]> {
    return this.httpClient.get<tenantResolverModel[]>("api/admin/tenants");
  }

  addTenant(param: {
    name: string,
    active: boolean,
    mode: string,
    subdomain: string
  }): Observable<tenantResolverModel> {
    return this.httpClient.post<tenantResolverModel>("api/admin/tenants", param);
  }

  accessIdentity(id: string): Observable<void> {
    return this.httpClient.post<void>(`api/recipient/rtips/${id}/iars`, {"request_motivation": ""});
  }

  requestAddAdminUser(param: NewUser): Observable<userResolverModel> {
    return this.httpClient.post<userResolverModel>("api/admin/users", param);
  }

  requestUpdateAdminUser(id: string, param: userResolverModel): Observable<userResolverModel> {
    return this.httpClient.put<userResolverModel>("api/admin/users/" + id, param);
  }

  requestDeleteAdminUser(id: string): Observable<userResolverModel> {
    return this.httpClient.delete<userResolverModel>("api/admin/users/" + id);
  }

  requestAddAdminContext(param: NewContext): Observable<contextResolverModel> {
    return this.httpClient.post<contextResolverModel>("api/admin/contexts", param);
  }

  requestAddAdminQuestionnaireStep(param: NewStep): Observable<Step> {
    return this.httpClient.post<Step>("api/admin/steps", param);
  }

  requestUpdateAdminQuestionnaireStep(id: string, param: Step): Observable<Step> {
    return this.httpClient.put<Step>("api/admin/steps/" + id, param);
  }

  requestDeleteAdminQuestionareStep(id: string): Observable<Step> {
    return this.httpClient.delete<Step>("api/admin/steps/" + id);
  }

  requestAddAdminQuestionnaireField(param: NewField): Observable<Field> {
    return this.httpClient.post<Field>("api/admin/fields", param);
  }

  requestAddAdminQuestionnaireFieldTemplate(param: FieldTemplate): Observable<FieldTemplate> {
    return this.httpClient.post<FieldTemplate>("api/admin/fieldtemplates", param);
  }

  requestUpdateAdminQuestionnaireField(id: string, param: Step | Field): Observable<Field> {
    return this.httpClient.put<Field>("api/admin/fields/" + id, param);
  }

  requestDeleteAdminQuestionareField(id: string): Observable<Field> {
    return this.httpClient.delete<Field>("api/admin/fields/" + id);
  }

  requestUpdateAdminContext(param: contextResolverModel, id: string): Observable<contextResolverModel> {
    return this.httpClient.put<contextResolverModel>("api/admin/contexts/" + id, param);
  }

  requestDeleteAdminContext(id: string): Observable<contextResolverModel> {
    return this.httpClient.delete<contextResolverModel>("api/admin/contexts/" + id);
  }

  requestDeleteStatus(url: string): Observable<Status> {
    return this.httpClient.delete<Status>(url);
  }

  requestUpdateStatus(url: string, param: Substatus | Status): Observable<Status> {
    const headers = {"content-type": "application/json"};
    return this.httpClient.put<Status>(url, param, {headers});
  }

  requestUpdateAdminNotification(notification: notificationResolverModel): Observable<notificationResolverModel> {
    return this.httpClient.put<notificationResolverModel>("api/admin/notification", notification);
  }

  requestCreateRedaction(content:RedactionData): Observable<RedactionData> {
    return this.httpClient.post<RedactionData>("api/recipient/redactions", content);
  }

  requestUpdateRedaction(data:RedactionData): Observable<RedactionData> {
    return this.httpClient.put<RedactionData>("api/recipient/redactions/"+ data.id, data);
  }

  requestAccreditationOE(data:AccreditationSubscriberModel): Observable<AccreditationSubscriberModel> {
    return this.httpClient.post<AccreditationSubscriberModel>("api/accreditation/request", data);
  }

  requestAccreditationFromInviteOE(uuid: string, data:AccreditationSubscriberModel): Observable<AccreditationSubscriberModel> {
    return this.httpClient.post<AccreditationSubscriberModel>("api/accreditation/request/"+uuid+"/confirm_invited", data);
  }

  requestUpdateOEAccredited(uuid: string, data: any) : Observable<any>{
    return this.httpClient.post<any>("api/accreditation/request/"+uuid+"/accredited", data);
  }

  runOperation(url: string, operation: string, args: any, refresh: boolean) {

    const data = {
      operation: operation,
      args: args
    };

    if (refresh) {
      setTimeout(() => {
        const currentUrl = this.router.url;
        this.router.navigateByUrl("routing", {skipLocationChange: true, replaceUrl: true}).then(() => {
          this.router.navigate([currentUrl]).then();
        });
      }, 150);
    }

    return this.httpClient.put(url, data);
  }

  tipOperation = (operation: string, args: any, tipId: string) => {
    const req = {
      "operation": operation,
      "args": args
    };
    return this.httpClient.put("api/recipient/rtips/" + tipId, req);
  };

  accreditorRequestResource(): Observable<EOExtendedInfo[]> {
    return this.httpClient.get<EOExtendedInfo[]>("api/accreditation/all");
  }

  sendAccreditationInvitation(id: string): Observable<void> {
    return this.httpClient.post<void>(`/api/accreditation/request/${id}/invited`, { responseType: 'text' as 'json'});
  }

  sendAccreditationApproved(id: string): Observable<void> {
    return this.httpClient.post<void>(`/api/accreditation/request/${id}/approved`, { responseType: 'text' as 'json'});
  }

  deleteAccreditationRequest(id: string, bodyReq: any): Observable<any> {
    return this.httpClient.delete<void>(`/api/accreditation/request/${id}`, {body : bodyReq});
  }

  updateStateOrganizationRequest(id: string, dataToUpdate: { 
    organization_name?: string, 
    organization_email?: string, 
    organization_institutional_site?: string, 
    type?: 'AFFILIATED' | 'NOT_AFFILIATED' 
  }): Observable<void> {
    return this.httpClient.put<void>(`/api/accreditation/request/${id}`, dataToUpdate);
  }

  toggleAccreditedOrganizationStatus(id: string): Observable<void> {
    return this.httpClient.put<void>(`/api/accreditation/request/${id}/toggle-status-active`, { responseType: 'text' as 'json'});
  }

  accreditorAccreditationDetail(org_id: string | null): Observable<ExternalOrganization>{
    return this.httpClient.get<any>("api/accreditation/request/"+org_id);
  }

  sendAccreditationRequest(dataToStore: EOInfo): Observable<void> {
    return this.httpClient.post<void>(`/api/accreditation/request/instructor_request`, dataToStore);
  }

}
