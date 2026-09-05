interface Mock {
  path: string;
  selector: string;
  mock: ((element: HTMLElement) => string) | string;
  value: string;
  type: "replace" | "add-before" | "add-after";
  language?: string;
  element?: HTMLElement;
  random?: string;
}

type Mocks = Record<string, Record<string, Mock[]>>;

class MockEngine {
  private mocks: Mocks = {};

  private applyMock(mock: Mock): void {
    const e = document.querySelector(mock.selector) as HTMLElement | null;
    if (e !== null && !e.classList.contains("Mock")) {
      e.classList.add("Mock");

      if (mock.type === "replace") {
        mock.element = e;
      } else {
        mock.element = document.createElement("div");
        if (mock.type === "add-before") {
          e.insertBefore(mock.element, e.childNodes[0] ?? null);
        } else if (mock.type === "add-after") {
          e.appendChild(mock.element);
        }
      }
    }

    if (mock.element) {
      let value;
      mock.language = window.GL.language;
      if (typeof mock.mock === "function") {
        value = mock.mock(mock.element);
      } else {
        value = mock.mock;
      }

      if (value && (!mock.value || mock.value != value)) {
        mock.random = Math.floor(Math.random() * 100000).toString();
      }

      if (mock.random && mock.element.getAttribute('MockRandomID') != mock.random) {
        mock.element.setAttribute('MockRandomID', mock.random);
        mock.element.innerHTML = mock.value = value;
      }
    }
  }

  run(): void {
    const current_path = document.location.pathname + document.location.hash.split("?")[0];

    for (const [path, selectors] of Object.entries(this.mocks)) {
      if (path === "*" || path === current_path) {
        for (const mocks of Object.values(selectors)) {
          for (const mock of mocks) {
            try {
              this.applyMock(mock);
            } catch {
              continue;
            }
          }
        }
      }
    }
  }

  public addMock(path: string, selector: string, mock: ((element: HTMLElement) => string) | string, type?: "replace" | "add-before" | "add-after"): void {
    const selectors = this.mocks[path] ?? (this.mocks[path] = {});
    const mocks = selectors[selector] ?? (selectors[selector] = []);

    if (type === undefined) {
      type = "replace";
    }

    mocks.push({"path": path, "selector": selector, "mock": mock, "value": "", "type": type});

    this.run();
  }
}

export const mockEngine = new MockEngine();
