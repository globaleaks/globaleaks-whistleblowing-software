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
          e.insertBefore(mock.element, e.childNodes[0]);
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
    let path, selector, i;

    for (path in this.mocks) {
      if (path === "*" || path === current_path) {
        for (selector in this.mocks[path]) {
          for (i in this.mocks[path][selector]) {
            try {
              this.applyMock(this.mocks[path][selector][i]);
            } catch (e) {
              continue;
            }
          }
        }
      }
    }
  }

  public addMock(path: string, selector: string, mock: ((element: HTMLElement) => string) | string, type?: "replace" | "add-before" | "add-after"): void {
    if (!(path in this.mocks)) {
      this.mocks[path] = {};
    }

    if (!(selector in this.mocks[path])) {
      this.mocks[path][selector] = [];
    }

    if (type === undefined) {
      type = "replace";
    }

    this.mocks[path][selector].push({"path": path, "selector": selector, "mock": mock, "value": "", "type": type});

    this.run();
  }
}

export const mockEngine = new MockEngine();
