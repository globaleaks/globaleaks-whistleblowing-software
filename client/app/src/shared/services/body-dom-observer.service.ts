import {Injectable, OnDestroy} from '@angular/core';
import {mockEngine} from "@app/services/helper/mocks";

@Injectable({
  providedIn: 'root',
})
export class BodyDomObserverService implements OnDestroy {
  private bodyObserver: MutationObserver | null = null;

  constructor() {
    this.observeBodyChanges();
  }

  private observeBodyChanges(): void {
    const bodyElement = document.body;

    this.bodyObserver = new MutationObserver(() => {
      mockEngine.run();
    });

    // Start observing for changes on the <body>
    this.bodyObserver.observe(bodyElement, {
      subtree: true,
      childList: true
    });
  }

  ngOnDestroy(): void {
    // Clean up the observer when the service/component is destroyed
    if (this.bodyObserver) {
      this.bodyObserver.disconnect();
    }
  }
}
