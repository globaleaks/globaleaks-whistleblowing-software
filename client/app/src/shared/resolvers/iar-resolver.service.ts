import {Injectable, inject} from "@angular/core";
import {Observable, of} from "rxjs";
import {map} from "rxjs/operators";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {IarData} from "@app/models/receiver/iar-data";

@Injectable({
  providedIn: "root"
})
export class IarResolver {
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  dataModel: IarData[] = [];

  reload() {
    this.httpService.iarResource().subscribe(
      (response: IarData[]) => {
        this.dataModel = response;
      }
    );
  }

  resolve(): Observable<boolean> {
    if (this.authenticationService.session.role === "custodian") {
      return this.httpService.iarResource().pipe(
        map((response: IarData[]) => {
          this.dataModel = response;
          return true;
        })
      );
    }
    return of(true);
  }
}
