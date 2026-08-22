import {effect, signal} from "@angular/core";
import {HttpResourceRef, httpResource} from "@angular/common/http";
import {Observable, of} from "rxjs";

/**
 * Base of the route resolvers backed by an httpResource.
 *
 * The resource is created disabled and starts loading the first time
 * resolve() finds the caller allowed; later calls reload it. resolve()
 * never blocks navigation: the loading panel of the HTTP interceptor
 * covers the page until the response lands and the consumers render the
 * signals exposed by `resource`.
 *
 * reload() coalesces: a resource ignores a reload requested while a load
 * is in flight, so the request is remembered and issued when the current
 * load settles. This keeps a burst of mutations (add, import, delete in
 * quick sequence) from leaving the list one response behind.
 */
export abstract class ResourceResolver<T> {
  readonly resource: HttpResourceRef<T>;

  private readonly enabled = signal(false);
  private pendingReload = false;

  protected constructor(url: string, defaultValue: T) {
    this.resource = httpResource<T>(() => this.enabled() ? url : undefined, {defaultValue});

    effect(() => {
      if (!this.resource.isLoading() && this.pendingReload) {
        this.pendingReload = false;
        this.resource.reload();
      }
    });
  }

  /** Compatibility accessor for the readers not yet converted to signals. */
  get dataModel(): T {
    return this.resource.value();
  }

  set dataModel(value: T) {
    this.resource.set(value);
  }

  protected abstract allowed(): boolean;

  resolve(): Observable<boolean> {
    if (this.allowed()) {
      this.reload();
    }

    return of(true);
  }

  reload(): void {
    if (!this.enabled()) {
      this.enabled.set(true);
      return;
    }

    if (!this.resource.reload()) {
      this.pendingReload = true;
    }
  }

  refresh(): void {
    this.reload();
  }
}
