import {Injectable, inject} from "@angular/core";
import {Observable, of, BehaviorSubject, switchMap, map} from "rxjs";
import {HttpService} from "@app/shared/services/http.service";
import {User} from "@app/models/resolvers/user-resolver-model";
import {AuthenticationService} from "@app/services/helper/authentication.service";

@Injectable({
  providedIn: "root"
})
export class UsersResolver {
  private httpService = inject(HttpService);
  private authenticationService = inject(AuthenticationService);

  private refreshTrigger = new BehaviorSubject<boolean>(true);

  dataModel: User[];

  constructor() {
    this.refreshTrigger.pipe(
      switchMap(() => this.fetchUsers())
    ).subscribe();
  }

  resolve(): Observable<boolean> {
    return this.refreshTrigger.pipe(
      switchMap(() => this.fetchUsers())
    );
  }

  private fetchUsers(): Observable<boolean> {
    return this.httpService.requestUsersResource().pipe(
      map((response: User[]) => {
        this.dataModel = response;
        return true;
      })
    );
  }

  refresh(): Observable<boolean> {
    const refresh$ = this.fetchUsers();
    this.refreshTrigger.next(true);
    return refresh$;
  }
}
