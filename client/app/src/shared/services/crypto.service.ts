import {Injectable, inject} from "@angular/core";
import {AppDataService} from "@app/app-data.service";
import {Observable, from, of} from "rxjs";
import {switchMap} from "rxjs/operators";

@Injectable({
  providedIn: "root"
})
export class CryptoService {
  private worker: Worker;
  private readonly pendingRequests = new Map<string, { resolve: (result: any) => void, reject: (error: any) => void }>();
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
    const array = new Uint32Array(16);
    window.crypto.getRandomValues(array);
    return Array.from(array, n => (n % 10).toString()).join('');
  }

  generatePassword(length = 16): string {
    const lower = "abcdefghijklmnopqrstuvwxyz";
    const upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    const digits = "0123456789";
    const special = "!@#$%^&*()-_=+[]";
    // Guarantee at least one character from each class so that the generated
    // password always satisfies the platform password strength requirements.
    const required = [lower, upper, digits, special];
    const all = lower + upper + digits + special;

    length = Math.max(length, required.length);

    const array = new Uint32Array(length);
    window.crypto.getRandomValues(array);

    const chars = Array.from(array, (n, i) => {
      const set = required[i] ?? all;
      return set.charAt(n % set.length);
    });

    // Shuffle so the guaranteed characters are not always at the beginning.
    const shuffle = new Uint32Array(length);
    window.crypto.getRandomValues(shuffle);
    for (let i = chars.length - 1; i > 0; i--) {
      const j = (shuffle[i] ?? 0) % (i + 1);
      const swapped = chars[j] ?? "";
      chars[j] = chars[i] ?? "";
      chars[i] = swapped;
    }

    return chars.join("");
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
    const data = this.str2Uint8Array(seed) as BufferSource; // Use str2Uint8Array
    const hashBuffer = await window.crypto.subtle.digest('SHA-256', data);
    const seedHash = new Uint8Array(hashBuffer);

    // Combine bytes (random or deterministic based on the seed)
    const combinedBytes = new Uint8Array(
      Array.from({ length: 16 }, (_, i) =>
        (seed ? seedHash[i] : randomBytes[i]) ?? 0
      )
    );

    // Return Base64-encoded salt
    return this.arrayToBase64(combinedBytes);
  }

  private readonly appDataService = inject(AppDataService);

  // The cost of the key derivation is the one the platform publishes: the
  // hashes stored embed it, so the client derives with the same parameters
  kdfOpslimit(): number {
    return this.appDataService.public?.node?.kdf_opslimit || 16;
  }

  kdfMemlimit(): number {
    const exponent = this.appDataService.public?.node?.kdf_memlimit;
    return 1 << (exponent || 27);
  }

  async hashArgon2(text: string, salt: string, iterations = this.kdfOpslimit(), memory: number = this.kdfMemlimit()): Promise<string> {
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

  // --- RFC 9449 DPoP -------------------------------------------------------

  private dpopKeyPair?: CryptoKeyPair;
  private dpopPublicJwk?: { kty: string; crv: string; x: string; y: string };
  // Offset (ms) between the server clock and this device's clock, learned from
  // the Date header of responses. It keeps the proof `iat` aligned to the
  // server so a skewed device clock does not make every request fail.
  private timeOffsetMs = 0;

  updateTimeOffset(serverDateMs: number): void {
    if (!isNaN(serverDateMs)) {
      this.timeOffsetMs = serverDateMs - Date.now();
    }
  }

  private base64urlFromBytes(bytes: Uint8Array): string {
    let binary = '';
    bytes.forEach((b) => {
      binary += String.fromCharCode(b);
    });
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }

  private base64urlFromString(str: string): string {
    return this.base64urlFromBytes(new TextEncoder().encode(str));
  }

  private async sha256Base64url(value: string): Promise<string> {
    const digest = await window.crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
    return this.base64urlFromBytes(new Uint8Array(digest));
  }

  private async getDpopKeyPair(): Promise<CryptoKeyPair> {
    if (!this.dpopKeyPair) {
      // The private key is generated non-extractable: it can sign DPoP proofs
      // but can never be exported or read back by the application. It lives only
      // in memory for the lifetime of the page, matching the in-memory session.
      this.dpopKeyPair = await window.crypto.subtle.generateKey(
        {name: 'ECDSA', namedCurve: 'P-256'},
        false,
        ['sign']
      );

      const jwk = await window.crypto.subtle.exportKey('jwk', this.dpopKeyPair.publicKey);
      this.dpopPublicJwk = {kty: 'EC', crv: 'P-256', x: jwk.x as string, y: jwk.y as string};
    }

    return this.dpopKeyPair;
  }

  async generateDpopProof(htm: string, htu: string, sessionId?: string): Promise<string> {
    const keyPair = await this.getDpopKeyPair();

    const header = {typ: 'dpop+jwt', alg: 'ES256', jwk: this.dpopPublicJwk};

    const jtiBytes = new Uint8Array(16);
    window.crypto.getRandomValues(jtiBytes);

    const payload: Record<string, string | number> = {
      htm,
      htu,
      iat: Math.floor((Date.now() + this.timeOffsetMs) / 1000),
      jti: this.base64urlFromBytes(jtiBytes)
    };

    if (sessionId) {
      payload['ath'] = await this.sha256Base64url(sessionId);
    }

    const signingInput = this.base64urlFromString(JSON.stringify(header)) + '.' +
                         this.base64urlFromString(JSON.stringify(payload));

    // WebCrypto ECDSA produces the raw R||S signature (IEEE P1363), which is
    // exactly the format that JWS ES256 requires.
    const signature = await window.crypto.subtle.sign(
      {name: 'ECDSA', hash: 'SHA-256'},
      keyPair.privateKey,
      new TextEncoder().encode(signingInput)
    );

    return signingInput + '.' + this.base64urlFromBytes(new Uint8Array(signature));
  }
}
