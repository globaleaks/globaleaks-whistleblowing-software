import {Injectable, inject} from "@angular/core";
import {Observable, of} from "rxjs";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {map} from "rxjs/operators";
import {RecipientReportsPage, RecipientReportsRequest, rtipResolverModel} from "@app/models/resolvers/rtips-resolver-model";
import {UtilsService} from "@app/shared/services/utils.service";
import {emptySearchQuery} from "@app/models/search/search-query";

@Injectable({
  providedIn: "root"
})
export class RTipsResolver {
  private readonly utilsService = inject(UtilsService);
  private readonly httpService = inject(HttpService);
  private readonly authenticationService = inject(AuthenticationService);

  dataModel: rtipResolverModel[] = [];
  total = 0;
  request: RecipientReportsRequest = {
    page: 1,
    search: "",
    unread: false,
    sort: "creation_date",
    descending: true,
    query: emptySearchQuery()
  };

  reload() {
    this.load(this.request).subscribe(
      () => {
        this.utilsService.reloadComponent();
      }
    );
  }

  load(request: RecipientReportsRequest): Observable<RecipientReportsPage> {
    this.request = request;
    return this.httpService.searchRecipientReports(request).pipe(
      map(response => {
        this.dataModel = response.reports;
        this.total = response.total;
        this.request = {...request, page: response.page};
        return response;
      })
    );
  }

  resolve(): Observable<boolean> {
    if (this.authenticationService.session?.role === "receiver") {
      return this.load({
        page: 1,
        search: "",
        unread: false,
        sort: "creation_date",
        descending: true,
        query: emptySearchQuery()
      }).pipe(
        map(() => {
          return true;
        })
      );
    }
    return of(true);
  }
}
