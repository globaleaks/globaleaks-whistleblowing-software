import { Injectable, inject } from "@angular/core";
import { PreferenceResolver } from "@app/shared/resolvers/preference.resolver";
import { Observable, of, throwError } from "rxjs";
import { HttpService } from "@app/shared/services/http.service";
import { nodeResolverModel } from "@app/models/resolvers/node-resolver-model";
import { AuthenticationService } from "@app/services/helper/authentication.service";
import { map, catchError } from "rxjs/operators";
import {Router} from "@angular/router";

@Injectable({
  providedIn: "root"
})
export class NodeResolver {
  private router = inject(Router);
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);
  private preferenceResolver = inject(PreferenceResolver);

  dataModel: nodeResolverModel = new nodeResolverModel();

  resolve(): Observable<boolean> {
    if (
        this.authenticationService.session.role === "admin" ||
        (this.authenticationService.session.role === "receiver" &&
            this.preferenceResolver.dataModel.can_edit_general_settings)
    ) {
      return this.httpService.requestNodeResource().pipe(
          map((response: nodeResolverModel) => {
            this.dataModel = response;
            return true;
          }),
          catchError((error: any) => {
            this.authenticationService.deleteSession();
            this.router.navigateByUrl('/login').then();
            return throwError(() => error);
          })
      );
    }
    return of(true);
  }
}
