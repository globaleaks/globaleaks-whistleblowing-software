import { Injectable, inject } from "@angular/core";
import {Observable, of} from "rxjs";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
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
    if (this.authenticationService.session.role === "admin") {
      return this.httpService.requestTipResource().pipe(
        map((response: tipsResolverModel) => {
          this.dataModel = response;
          return true;
        })
      );
    }
    return of(true);
  }

}
