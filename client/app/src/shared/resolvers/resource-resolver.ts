import {effect, signal} from "@angular/core";
import {toObservable} from "@angular/core/rxjs-interop";
import {HttpResourceRef, httpResource} from "@angular/common/http";
import {Observable, of, throwError} from "rxjs";
import {filter, skipWhile, switchMap, take} from "rxjs/operators";

type ResourceStatus = HttpResourceRef<unknown>["status"] extends () => infer S ? S : never;

const isLoading = (status: ResourceStatus): boolean => status === "loading" || status === "reloading";

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
 *
 * Resolvers whose data drives decisions taken at construction time
 * (redirects, session checks) override resolve() with resolveAndWait(),
 * which completes only once the load has settled.
 */
export abstract class ResourceResolver<T> {
  readonly resource: HttpResourceRef<T>;

  private readonly enabled = signal(false);
  private readonly status$: Observable<ResourceStatus>;
  private pendingReload = false;

  protected constructor(url: string, defaultValue: T) {
    this.resource = httpResource<T>(() => this.enabled() ? url : undefined, {defaultValue});
    this.status$ = toObservable(this.resource.status);

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

  /**
   * Starts a (re)load and completes when it has settled: the status is
   * observed until it has been seen loading and is loading no more.
   */
  protected resolveAndWait(): Observable<boolean> {
    this.reload();

    return this.status$.pipe(
      skipWhile((status) => !isLoading(status)),
      filter((status) => !isLoading(status)),
      take(1),
      switchMap((status) => status === "error" ? this.onError(this.resource.error()) : of(true))
    );
  }

  protected onError(error: unknown): Observable<boolean> {
    return throwError(() => error);
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
