import { Injectable, inject } from "@angular/core";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {Observable, of} from "rxjs";
import {WbTipData} from "@app/models/whistleblower/wb-tip-data";
import {HttpService} from "@app/shared/services/http.service";
import {map} from "rxjs/operators";

@Injectable({
  providedIn: "root"
})
export class WbTipResolver {
  private authenticationService = inject(AuthenticationService);
  private httpService = inject(HttpService);


  dataModel: WbTipData;

  onReload(callback: () => void) {
    this.httpService.whistleBlowerTip().subscribe(
      (response: WbTipData) => {
        this.dataModel = response;
        callback();
      }
    );
  }

  resolve(): Observable<boolean> {

    if (!this.dataModel && this.authenticationService.session && this.authenticationService.session.role === "whistleblower") {
      return this.httpService.whistleBlowerTip().pipe(
        map((response: WbTipData) => {
          this.dataModel = response;
          return true;
        })
      );
    }
    return of(true);
  }
}
