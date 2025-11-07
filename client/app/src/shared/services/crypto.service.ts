import {Injectable} from "@angular/core";
import {Observable, from, of} from "rxjs";
import {switchMap} from "rxjs/operators";
import * as sodium from 'libsodium-wrappers-sumo';

@Injectable({
  providedIn: "root"
})
export class CryptoService {
  private worker: Worker;
  private pendingRequests = new Map<string, { resolve: (result: any) => void, reject: (error: any) => void }>();
  private messageId = 0;

  initializeWorker() {
    if (this.worker) {
      return;
    }

    this.worker = new Worker('/workers/crypto.worker.js', { type: 'module' });

    this.worker.onmessage = (event: MessageEvent) => {
      const { id, success, result, error } = event.data;

      const request = this.pendingRequests.get(id);

      if (request) {
        // Remove the resolved request from the map
        this.pendingRequests.delete(id);

        if (success) {
          request.resolve(result);
        } else {
          // Reject the promise with the error message
          request.reject(error);
        }
      }
    };
  }

  generateReceipt(): string {
    const array = new Uint8Array(16); // Create a byte array of length 16
    window.crypto.getRandomValues(array); // Fill it with secure random values
    return Array.from(array, byte => (byte % 10).toString()).join('');
  }

  str2Uint8Array(str: string): Uint8Array {
    const result = new Uint8Array(str.length);
    for (let i = 0; i < str.length; i++) {
      result[i] = str.charCodeAt(i);
    }
    return result;
  }

  arrayToBase64(array: Uint8Array): string {
    let binary = '';
    array.forEach((byte) => {
      binary += String.fromCharCode(byte);
    });
    return btoa(binary);
  }

  async generateSalt(seed = ''): Promise<string> {
    // Generate 16 random bytes
    const randomBytes = new Uint8Array(16);
    window.crypto.getRandomValues(randomBytes);

    // Compute the SHA-256 hash of the seed if provided
    const data = this.str2Uint8Array(seed); // Use str2Uint8Array
    const hashBuffer = await window.crypto.subtle.digest('SHA-256', data);
    const seedHash = new Uint8Array(hashBuffer);

    // Combine bytes (random or deterministic based on the seed)
    const combinedBytes = new Uint8Array(
      Array.from({ length: 16 }, (_, i) =>
        seed ? seedHash[i] : randomBytes[i]
      )
    );

    // Return Base64-encoded salt
    return this.arrayToBase64(combinedBytes);
  }

  async hashArgon2(text: string, salt: string, iterations = 16, memory: number = 1 << 27): Promise<string> {
    this.initializeWorker();

    const id = (this.messageId++).toString();

    return new Promise((resolve, reject) => {
      this.pendingRequests.set(id, { resolve, reject });

      // Post data to the worker
      this.worker.postMessage({
        id,
        text,
        salt,
        iterations,
	memory
      });
    });
  }

  work(text: string, salt: string, iterations: number, memory: number, counter: number): Observable<number> {
    return from(this.hashArgon2(text + String(counter), salt, iterations, memory)).pipe(
      switchMap((hash) => {
        if (atob(hash).charCodeAt(31) === 0) {
          return of(counter);
        } else {
          return this.work(text, salt, iterations, memory, counter + 1);
        }
      })
    );
  }

  proofOfWork(token: any): Observable<number> {
    this.initializeWorker();
    return this.work(token.id, token.salt, 1, 1 << 20, 0);
  }
}
