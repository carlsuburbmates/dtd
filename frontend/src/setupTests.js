import "@testing-library/jest-dom";
import { vi } from "vitest";

// Make vi accessible globally as jest for backward-compatibility with Jest-syntax tests
globalThis.jest = vi;
