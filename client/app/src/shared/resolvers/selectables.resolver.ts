import {Injectable, inject} from "@angular/core";
import {Observable, map} from "rxjs";
import {HttpService} from "@app/shared/services/http.service";
import {Selectables} from "@app/models/app/selectables";

@Injectable({
  providedIn: "root"
})
export class SelectablesResolver {
  private httpService = inject(HttpService);

  dataModel: Selectables = {users: [], contexts: [], questionnaires: [], user_profiles: []};

  resolve(): Observable<boolean> {
    return this.httpService.requestSelectablesResource().pipe(
      map((response: Selectables) => {
        this.dataModel = response;
        return true;
      })
    );
  }

  refresh(): Observable<boolean> {
    return this.resolve();
  }
}
