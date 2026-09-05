import {Injectable, inject} from "@angular/core";
import {Observable, of} from "rxjs";
import {switchMap} from "rxjs/operators";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {auditLogArea} from "@app/shared/partials/auditlog/auditlog-area";
import {auditlogResolverModel} from "@app/models/resolvers/auditlog-resolver-model";

@Injectable({
  providedIn: "root"
})
export class AuditLogResolver {
  private readonly httpService = inject(HttpService);
  private readonly authenticationService = inject(AuthenticationService);

  dataModel: auditlogResolverModel = new auditlogResolverModel();

  resolve(): Observable<boolean> {
    // The log is read on the area of the role in session: the administrator
    // and the auditor reach the same implementation, each on its own path
    const area = auditLogArea(this.authenticationService.session?.role ?? "");

    if (area) {
      return this.httpService.requestAuditLogResource(area).pipe(
        switchMap((response: auditlogResolverModel) => {
          this.handleResponse(response);
          return of(true);
        })
      );
    }
    return of(true);
  }


  private handleResponse(response: auditlogResolverModel): void {
    this.dataModel = response;
  }
}
