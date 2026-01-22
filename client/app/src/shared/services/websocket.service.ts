import { Injectable } from '@angular/core';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';

@Injectable({ providedIn: 'root' })
export class PushService {
  socket$!: WebSocketSubject<any>;

  connect(session_id: string, tipIds: string[]) {
    this.socket$ = webSocket('ws://localhost:9000');
    this.socket$.next({
      type: 'auth',
      session_id: session_id,
      tip_ids: tipIds
    });
  }

  disconnect() {
    if (this.socket$) {
      this.socket$.complete();
    }
  }
}
