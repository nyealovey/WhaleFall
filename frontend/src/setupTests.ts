import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

function createTestRect(width = 1024, height = 320): DOMRectReadOnly {
  return {
    bottom: height,
    height,
    left: 0,
    right: width,
    top: 0,
    width,
    x: 0,
    y: 0,
    toJSON: () => ({})
  };
}

class ResizeObserverMock {
  private readonly callback: ResizeObserverCallback;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
  }

  observe(target: Element) {
    this.trigger(target);
  }
  unobserve() {}
  disconnect() {}

  trigger(target: Element) {
    const contentRect = createTestRect();
    this.callback([{ target, contentRect } as ResizeObserverEntry], this as unknown as ResizeObserver);
  }
}

vi.stubGlobal("ResizeObserver", ResizeObserverMock);

const originalGetBoundingClientRect = window.HTMLElement.prototype.getBoundingClientRect;

Object.defineProperty(window.HTMLElement.prototype, "getBoundingClientRect", {
  value() {
    const rect = originalGetBoundingClientRect.call(this);
    if (rect.width > 0 || rect.height > 0) {
      return rect;
    }
    return createTestRect();
  }
});

if (!window.HTMLElement.prototype.hasPointerCapture) {
  Object.defineProperty(window.HTMLElement.prototype, "hasPointerCapture", {
    value: () => false
  });
}

if (!window.HTMLElement.prototype.releasePointerCapture) {
  Object.defineProperty(window.HTMLElement.prototype, "releasePointerCapture", {
    value: () => undefined
  });
}

if (!window.HTMLElement.prototype.scrollIntoView) {
  Object.defineProperty(window.HTMLElement.prototype, "scrollIntoView", {
    value: () => undefined
  });
}

afterEach(() => {
  cleanup();
});
