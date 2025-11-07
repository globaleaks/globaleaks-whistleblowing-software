import { Injectable } from '@angular/core';
import { Renderer } from 'marked';

interface Link {
  href: string;
  title?: string | null;
  tokens?: any[];
}

@Injectable({
  providedIn: 'root',
})
export class MarkdownRendererService {
  constructor() {}

  getCustomRenderer(): Renderer {
    const customRenderer = new Renderer();

    customRenderer.link = ({ href, title, tokens }: Link): string => {
      const text = tokens?.[0]?.raw || href;

      // Detect if the markdown code includes images
      const match = text.match(/!\[(.*?)\]\((.*?)\)/);

      return match
        ? `<a href="${href}"><img src="${match[2]}" alt="${match[1]}" /></a>`
        : `<a href="${href}"${title ? ` title="${title}"` : ''}>${text}</a>`;
    };

    return customRenderer;
  }
}
