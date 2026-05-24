import { Injectable } from '@angular/core';
import { Renderer } from 'marked';

@Injectable({
  providedIn: 'root',
})
export class MarkdownRendererService {
  constructor() {}

  getCustomRenderer(): Renderer {
    const renderer = new Renderer();
    const defaultLink = Renderer.prototype.link;

    renderer.link = function (token: any) {
      const html = defaultLink.call(this, token);
      return html.startsWith('<a ')
        ? '<a target="_blank" rel="noopener noreferrer" ' + html.slice(3)
        : html;
    };

    return renderer;
  }
}
