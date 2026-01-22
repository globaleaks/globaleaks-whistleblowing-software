import { Injectable } from '@angular/core';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';

@Injectable({ providedIn: 'root' })
export class PushService {
  socket$!: WebSocketSubject<any>;

  connect(session_id: string, tipIds: string[]) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host; // includes hostname + port

    const wsUrl = `${protocol}//${host}/ws`;

    this.socket$ = webSocket(wsUrl);

    this.socket$.next({
      type: 'auth',
      session_id,
      tip_ids: tipIds
    });
  }

  disconnect() {
    this.socket$?.complete();
  }
}
