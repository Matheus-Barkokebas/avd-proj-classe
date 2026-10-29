import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  localStorage.clear();
});

// jsdom não implementa matchMedia (usado para o tema do sistema)
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (consulta: string) => ({
    matches: false, media: consulta, onchange: null,
    addListener: () => {}, removeListener: () => {}, addEventListener: () => {}, removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});
