import {Injectable, inject} from "@angular/core";
import {Observable, of} from "rxjs";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {map} from "rxjs/operators";
import {rtipResolverModel} from "@app/models/resolvers/rtips-resolver-model";
import {UtilsService} from "@app/shared/services/utils.service";

@Injectable({
  providedIn: "root"
})
export class RTipsResolver {
  private utilsService = inject(UtilsService);
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  dataModel: rtipResolverModel[] = [];

  reload() {
    this.httpService.receiverTipResource().subscribe(
      (response) => {
        this.dataModel = response;
        this.utilsService.reloadComponent();
      }
    );
  }

  resolve(): Observable<boolean> {
    if (this.authenticationService.session.role === "receiver") {
      return this.httpService.receiverTipResource().pipe(
        map((response) => {
          this.dataModel = response;
          return true;
        })
      );
    }
    return of(true);
  }
}
