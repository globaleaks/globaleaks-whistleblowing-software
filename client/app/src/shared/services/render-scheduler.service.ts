import {ApplicationRef, Injectable, Injector, inject} from "@angular/core";

/**
 * Single entry point to request a rendering pass in zoneless mode.
 *
 * Without zone.js Angular re-renders only after template event listeners,
 * signal updates, markForCheck() or view creation. State mutated in any other
 * asynchronous continuation (HttpClient subscribe callbacks, timers, Promises,
 * upload library callbacks, ...) stays invisible until something unrelated
 * triggers a rendering pass: that is the class of defects where a page looks
 * frozen until the user clicks anywhere.
 *
 * schedule() marks the root views for check: Angular's own change detection
 * scheduler then coalesces the requests and runs a single pass asynchronously,
 * i.e. after every synchronous callback in the current stack has finished
 * mutating state. Note that ApplicationRef.tick() would not do: in zoneless
 * mode it refreshes only views already marked dirty.
 */
@Injectable({
  providedIn: "root"
})
export class RenderSchedulerService {
  // ApplicationRef is resolved lazily: this service is reached through the
  // HTTP interceptors, which may run before ApplicationRef is constructed.
  private readonly injector = inject(Injector);

  schedule(): void {
    const appRef = this.injector.get(ApplicationRef);

    if (appRef.destroyed) {
      return;
    }

    for (const component of appRef.components) {
      component.changeDetectorRef.markForCheck();
    }
  }
}
