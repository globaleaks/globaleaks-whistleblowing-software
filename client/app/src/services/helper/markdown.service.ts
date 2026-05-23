import { Injectable } from '@angular/core';
import { Renderer } from 'marked';

@Injectable({
  providedIn: 'root',
})
export class MarkdownRendererService {
  constructor() {}

  getCustomRenderer(): Renderer {
    const renderer = new Renderer();
    const defaultLink = renderer.link.bind(renderer);

    renderer.link = function (token) {
      const html = defaultLink(token);
      return html.startsWith('<a ')
        ? '<a target="_blank" rel="noopener noreferrer" ' + html.slice(3)
        : html;
    };

    return renderer;
  }
}
