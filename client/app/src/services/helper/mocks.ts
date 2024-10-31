interface Mock {
  path: string;
  selector: string;
  mock: ((element: Element) => string) | string;
  value: string;
  type: "replace" | "add-before" | "add-after";
  language?: string;
}

interface Mocks {
  [path: string]: {
    [selector: string]: Mock[];
  };
}

class MockEngine {
  private mocks: Mocks = {};

  private applyMock(mock: Mock): void {
    const e = document.querySelector(mock.selector) as HTMLElement | null;
    if (e) {
      if (!mock.value || mock.language !== GL.language) {
        mock.language = GL.language;
        if (typeof mock.mock === "function") {
          mock.value = mock.mock(e);
        } else {
          mock.value = mock.mock;
        }
      }

      if (mock.type === "replace") {
        if (mock.value && e.innerHTML !== mock.value) {
          e.innerHTML = mock.value;
        }

        if (mock.value) {
          mock.value = e.innerHTML;
        }
      } else {
        let custom_elem = e.querySelector(".Mock") as HTMLElement | null;

        if (!custom_elem) {
          custom_elem = document.createElement("div");
          custom_elem.classList.add("Mock");
        }

        custom_elem.innerHTML = mock.value;

        if (mock.type === "add-before") {
          e.insertBefore(custom_elem, e.childNodes[0]);
        } else if (mock.type === "add-after") {
          e.appendChild(custom_elem);
        }
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

  public addMock(path: string, selector: string, mock: ((element: Element) => string) | string, type?: "replace" | "add-before" | "add-after"): void {
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

const GL = {
  language: 'en',
  get mockEngine() {
    return mockEngine;
  }
};

export const mockEngine = new MockEngine();