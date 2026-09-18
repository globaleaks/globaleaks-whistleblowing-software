// trusted-types.service.ts
import { Injectable } from '@angular/core';
import DOMPurify from 'dompurify';

@Injectable({
  providedIn: 'root',
})
export class TrustedTypesService {
  constructor() {
    if ((window as any).trustedTypes) {
      (window as any).trustedTypes.createPolicy('default', {
        createHTML: (input: string) => {
          // Sanitize the input using DOMPurify or any other sanitizer library
          return (DOMPurify.sanitize(input, { RETURN_TRUSTED_TYPE: true }) as unknown) as string;
        },
        createScript: () => {
          throw new Error('Scripts are not allowed by this policy.');
        },
        createScriptURL: (input: string) => {
          if (['/s/script', '/workers/crypto.worker.js'].indexOf(input) !== -1) {
            return input;
          } else {
            throw new Error('Script URLs are not allowed by this policy.');
          }
        }
      });
    }
  }
}
