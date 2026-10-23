import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import SuburbCombobox from "./SuburbCombobox";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

describe("SuburbCombobox", () => {
  let container;
  let root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it("renders input with correct placeholder, id and accessibility attributes", () => {
    act(() => {
      root.render(
        <SuburbCombobox
          id="match-suburb"
          dataTestId="match-suburb"
          value=""
          placeholder="e.g. Richmond or 3121"
        />
      );
    });

    const input = container.querySelector("#match-suburb");
    expect(input).not.toBeNull();
    expect(input.getAttribute("role")).toBe("combobox");
    expect(input.getAttribute("placeholder")).toBe("e.g. Richmond or 3121");
    expect(input.getAttribute("aria-expanded")).toBe("false");
  });

  it("opens zero-state with popular Melbourne hubs on focus", () => {
    act(() => {
      root.render(
        <SuburbCombobox
          id="match-suburb"
          dataTestId="match-suburb"
          value=""
        />
      );
    });

    const input = container.querySelector("#match-suburb");
    act(() => {
      input.focus();
    });

    const listbox = container.querySelector("#match-suburb-listbox");
    expect(listbox).not.toBeNull();
    expect(input.getAttribute("aria-expanded")).toBe("true");
    expect(listbox.textContent).toContain("Popular Melbourne Hubs");
    expect(listbox.textContent).toContain("Richmond");
    expect(listbox.textContent).toContain("Brunswick");
  });

  it("filters suggestions by suburb name and postcode", () => {
    const handleChange = vi.fn();

    act(() => {
      root.render(
        <SuburbCombobox
          id="match-suburb"
          dataTestId="match-suburb"
          value="Fitz"
          onChange={handleChange}
        />
      );
    });

    const input = container.querySelector("#match-suburb");
    act(() => {
      input.focus();
    });

    const listbox = container.querySelector("#match-suburb-listbox");
    expect(listbox).not.toBeNull();
    expect(listbox.textContent).toContain("Fitzroy");
    expect(listbox.textContent).toContain("3065");

    // Change value to postcode
    act(() => {
      root.render(
        <SuburbCombobox
          id="match-suburb"
          dataTestId="match-suburb"
          value="3121"
          onChange={handleChange}
        />
      );
    });

    expect(container.textContent).toContain("Richmond");
    expect(container.textContent).toContain("3121");
  });

  it("allows selecting a suburb with mouse click", () => {
    const handleChange = vi.fn();
    const handleSelect = vi.fn();

    act(() => {
      root.render(
        <SuburbCombobox
          id="match-suburb"
          dataTestId="match-suburb"
          value="Rich"
          onChange={handleChange}
          onSelect={handleSelect}
        />
      );
    });

    const input = container.querySelector("#match-suburb");
    act(() => {
      input.focus();
    });

    const option = container.querySelector("#match-suburb-item-0");
    expect(option).not.toBeNull();

    act(() => {
      option.click();
    });

    expect(handleChange).toHaveBeenCalledWith(
      expect.objectContaining({
        target: expect.objectContaining({ value: "Richmond" }),
      })
    );
    expect(handleSelect).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Richmond" })
    );
  });

  it("closes dropdown on Escape key", () => {
    act(() => {
      root.render(
        <SuburbCombobox
          id="match-suburb"
          dataTestId="match-suburb"
          value="Carlton"
        />
      );
    });

    const input = container.querySelector("#match-suburb");
    act(() => {
      input.focus();
    });

    expect(container.querySelector("#match-suburb-listbox")).not.toBeNull();

    act(() => {
      input.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    });

    expect(container.querySelector("#match-suburb-listbox")).toBeNull();
  });
});
