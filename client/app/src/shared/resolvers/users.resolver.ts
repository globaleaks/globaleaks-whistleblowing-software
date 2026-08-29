import {Injectable} from "@angular/core";
import {User} from "@app/models/resolvers/user-resolver-model";
import {ResourceResolver} from "@app/shared/resolvers/resource-resolver";

@Injectable({
  providedIn: "root"
})
export class UsersResolver extends ResourceResolver<User[]> {
  constructor() {
    super("api/admin/users", []);
  }

  protected allowed(): boolean {
    return true;
  }
}
