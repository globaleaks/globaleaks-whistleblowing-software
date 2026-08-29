import {Injectable, inject} from "@angular/core";
import {Observable, of} from "rxjs";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {auditLogArea} from "@app/shared/partials/auditlog/auditlog-area";
import {tipsResolverModel} from "@app/models/resolvers/tips-resolver-model";
import {map} from "rxjs/operators";

@Injectable({
  providedIn: "root"
})
export class TipsResolver {
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  dataModel: tipsResolverModel = new tipsResolverModel();

  resolve(): Observable<boolean> {
    // The log is read on the area of the role in session: the administrator
    // and the auditor reach the same implementation, each on its own path
    const area = auditLogArea(this.authenticationService.session.role);

    if (area) {
      return this.httpService.requestAuditLogTipsResource(area).pipe(
        map((response: tipsResolverModel) => {
          this.dataModel = response;
          return true;
        })
      );
    }
    return of(true);
  }

}
