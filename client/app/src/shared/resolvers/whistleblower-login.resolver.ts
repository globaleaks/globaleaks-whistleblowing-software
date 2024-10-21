import { Injectable, inject } from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {Observable, of} from "rxjs";

@Injectable({
  providedIn: "root"
})
export class WhistleblowerLoginResolver {
  private appDataService = inject(AppDataService);
  private authenticationService = inject(AuthenticationService);


  resolve(): Observable<boolean> {
    if (this.appDataService.page === "submissionpage") {
      setTimeout(() => {
        this.authenticationService.login(0, "whistleblower", "");
      }, 0);
    }
    return of(true);
  }
}
