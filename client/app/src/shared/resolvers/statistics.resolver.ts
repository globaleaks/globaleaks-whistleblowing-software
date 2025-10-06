import {Injectable, inject} from "@angular/core";
import {Observable, of} from "rxjs";
import {HttpService} from "@app/shared/services/http.service";
import {AuthenticationService} from "@app/services/helper/authentication.service";
import {map, catchError} from "rxjs/operators";
import {statisticsResolverModel} from "@app/models/resolvers/statistics-resolver-model";

@Injectable({
  providedIn: "root"
})
export class StatisticsResolver {
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  dataModel: statisticsResolverModel;

  resolve(filters?: {
    context_id?: string, 
    status?: string[], 
    tags?: string[], 
    tenant?: string[], 
    channel?: string[], 
    date_from?: number, 
    date_to?: number
  }): Observable<boolean> {
    if (this.authenticationService.session?.role === "analyst") {
      return this.httpService.requestStatisticsResource(filters).pipe(
        map((response) => {
          this.dataModel = response;
          return true;
        }),
        catchError(() => of(false))
      );
    }
    
    return of(true);
  }
  
  // Method to get filtered statistics
  getFilteredStatistics(filters?: {
    context_id?: string, 
    status?: string[], 
    tags?: string[], 
    tenant?: string[], 
    channel?: string[], 
    date_from?: number, 
    date_to?: number
  }): Observable<statisticsResolverModel> {
    if (this.authenticationService.session.role === "analyst") {
      return this.httpService.requestStatisticsResource(filters);
    }
    return of(this.dataModel || {} as statisticsResolverModel);
  }
}
