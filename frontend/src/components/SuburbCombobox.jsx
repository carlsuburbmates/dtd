import React, { useState, useRef, useEffect, useMemo } from "react";
import { MapPin, Search, X, ChevronDown } from "lucide-react";
import { MELBOURNE_SUBURBS } from "@/data/melbourneSuburbs";

// Curated popular hubs for zero-input / initial focus state
const POPULAR_HUBS = [
  "Richmond",
  "South Yarra",
  "Brunswick",
  "St Kilda",
  "Fitzroy",
  "Werribee",
  "Carlton",
  "Hawthorn",
];

export default function SuburbCombobox({
  id = "match-suburb",
  dataTestId = "match-suburb",
  value = "",
  onChange,
  onSelect,
  placeholder = "e.g. Richmond or 3121",
  required = false,
  className = "",
  availableSuburbs = [], // optional filter from /config
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const containerRef = useRef(null);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  // Build catalogue: prefer rich MELBOURNE_SUBURBS, augmented with any extra names from config
  const catalogue = useMemo(() => {
    const map = new Map();
    MELBOURNE_SUBURBS.forEach((item) => {
      map.set(item.name.toLowerCase(), item);
    });
    if (Array.isArray(availableSuburbs)) {
      availableSuburbs.forEach((name) => {
        const lower = String(name).toLowerCase();
        if (!map.has(lower)) {
          map.set(lower, { name: String(name), postcode: "", region: "Greater Melbourne" });
        }
      });
    }
    return Array.from(map.values());
  }, [availableSuburbs]);

  // Filter results based on current input value
  const filteredSuburbs = useMemo(() => {
    const query = (value || "").trim().toLowerCase();
    if (!query) {
      // Zero-input state: return popular hubs
      return catalogue.filter((item) =>
        POPULAR_HUBS.some((hub) => hub.toLowerCase() === item.name.toLowerCase())
      );
    }

    // Match by suburb name starting with query, then containing query, or postcode match
    const isNumeric = /^\d+$/.test(query);

    return catalogue
      .filter((item) => {
        if (isNumeric) {
          return item.postcode.startsWith(query);
        }
        return (
          item.name.toLowerCase().includes(query) ||
          item.postcode.startsWith(query)
        );
      })
      .sort((a, b) => {
        const aName = a.name.toLowerCase();
        const bName = b.name.toLowerCase();
        // Priority to exact startsWith
        const aStarts = aName.startsWith(query);
        const bStarts = bName.startsWith(query);
        if (aStarts && !bStarts) return -1;
        if (!aStarts && bStarts) return 1;
        return aName.localeCompare(bName);
      })
      .slice(0, 8); // Cap to 8 items to prevent cognitive overload
  }, [catalogue, value]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Reset active index when suggestions change
  useEffect(() => {
    setActiveIndex(-1);
  }, [filteredSuburbs]);

  // Scroll active item into view
  useEffect(() => {
    if (activeIndex >= 0 && listRef.current) {
      const activeEl = listRef.current.children[activeIndex];
      if (activeEl && typeof activeEl.scrollIntoView === "function") {
        activeEl.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    }
  }, [activeIndex]);

  const handleSelect = (suburb) => {
    const selectedName = suburb.name;
    if (onChange) {
      onChange({ target: { value: selectedName, id, name: id } });
    }
    if (onSelect) {
      onSelect(suburb);
    }
    setIsOpen(false);
    inputRef.current?.focus();
  };

  const handleClear = (e) => {
    e.stopPropagation();
    if (onChange) {
      onChange({ target: { value: "", id, name: id } });
    }
    setIsOpen(true);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e) => {
    if (!isOpen && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      setIsOpen(true);
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) =>
        prev < filteredSuburbs.length - 1 ? prev + 1 : 0
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) =>
        prev > 0 ? prev - 1 : filteredSuburbs.length - 1
      );
    } else if (e.key === "Enter") {
      if (isOpen && activeIndex >= 0 && filteredSuburbs[activeIndex]) {
        e.preventDefault();
        handleSelect(filteredSuburbs[activeIndex]);
      }
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  // Helper to bold matching characters
  const renderHighlighted = (text, query) => {
    if (!query || !query.trim()) return text;
    const q = query.trim().toLowerCase();
    const index = text.toLowerCase().indexOf(q);
    if (index === -1) return text;
    const before = text.slice(0, index);
    const match = text.slice(index, index + q.length);
    const after = text.slice(index + q.length);
    return (
      <>
        {before}
        <span className="font-bold text-[#1A3A32] underline decoration-[#1A3A32]/30 decoration-2 underline-offset-2">
          {match}
        </span>
        {after}
      </>
    );
  };

  const isZeroState = !value || !value.trim();

  return (
    <div ref={containerRef} className="relative w-full">
      {/* Input Field with contextual icons */}
      <div className="relative flex items-center">
        <span className="absolute left-3.5 flex items-center pointer-events-none text-[#5C6D59]">
          <MapPin className="w-4 h-4" aria-hidden="true" />
        </span>

        <input
          ref={inputRef}
          id={id}
          data-testid={dataTestId}
          type="text"
          role="combobox"
          aria-expanded={isOpen}
          aria-autocomplete="list"
          aria-controls={`${id}-listbox`}
          aria-activedescendant={
            activeIndex >= 0 ? `${id}-item-${activeIndex}` : undefined
          }
          className={`w-full bg-white border border-[#E5DFD3] rounded-xl pl-10 pr-10 py-3.5 text-sm text-[#1A3A32] placeholder-[#4A615A]/60 focus:outline-none focus:border-[#1A3A32] focus:ring-2 focus:ring-[#1A3A32]/10 transition-all shadow-sm ${className}`}
          placeholder={placeholder}
          value={value}
          onChange={(e) => {
            if (onChange) onChange(e);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          autoComplete="off"
          required={required}
        />

        {/* Clear button or Chevron */}
        <div className="absolute right-3 flex items-center">
          {value ? (
            <button
              type="button"
              onClick={handleClear}
              className="p-1 rounded-full text-[#5C6D59] hover:text-[#1A3A32] hover:bg-[#F5F2EB] transition-colors focus:outline-none"
              aria-label="Clear suburb search"
            >
              <X className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setIsOpen(!isOpen)}
              className="p-1 rounded-full text-[#5C6D59] hover:text-[#1A3A32] transition-colors focus:outline-none"
              aria-label="Toggle suburb list"
              tabIndex={-1}
            >
              <ChevronDown
                className={`w-4 h-4 transition-transform duration-200 ${
                  isOpen ? "rotate-180" : ""
                }`}
              />
            </button>
          )}
        </div>
      </div>

      {/* Modern Popover Dropdown Tray */}
      {isOpen && (
        <div
          id={`${id}-listbox`}
          role="listbox"
          className="absolute z-50 left-0 right-0 mt-2 bg-white/95 backdrop-blur-md border border-[#E5DFD3] rounded-2xl shadow-xl shadow-stone-900/10 overflow-hidden transition-all duration-150 animate-in fade-in-0 slide-in-from-top-1"
        >
          {/* Section Header */}
          <div className="px-4 pt-3 pb-1.5 text-[10px] font-bold tracking-wider uppercase text-[#5C6D59] border-b border-[#E5DFD3]/60 bg-[#FAFAF7]/50 flex justify-between items-center">
            <span>{isZeroState ? "Popular Melbourne Hubs" : "Greater Melbourne Suburbs"}</span>
            <span className="text-[10px] font-normal lowercase tracking-normal text-[#4A615A]/70">
              {filteredSuburbs.length} {filteredSuburbs.length === 1 ? "result" : "suggestions"}
            </span>
          </div>

          {/* List items */}
          <div ref={listRef} className="max-h-64 overflow-y-auto py-1 divide-y divide-[#E5DFD3]/30">
            {filteredSuburbs.length > 0 ? (
              filteredSuburbs.map((suburb, index) => {
                const isSelected = activeIndex === index;
                return (
                  <div
                    key={`${suburb.name}-${suburb.postcode}-${index}`}
                    id={`${id}-item-${index}`}
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => handleSelect(suburb)}
                    onMouseEnter={() => setActiveIndex(index)}
                    className={`flex items-center justify-between px-4 py-2.5 cursor-pointer text-sm transition-colors duration-100 ${
                      isSelected
                        ? "bg-[#E8EFEA] text-[#1A3A32] font-medium"
                        : "text-[#1A3A32] hover:bg-[#F5F2EB]/80"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span
                        className={`p-1 rounded-md transition-colors ${
                          isSelected
                            ? "bg-[#1A3A32] text-white"
                            : "bg-[#FAFAF7] text-[#5C6D59] border border-[#E5DFD3]/80"
                        }`}
                      >
                        <MapPin className="w-3.5 h-3.5 shrink-0" />
                      </span>
                      <div className="truncate">
                        <span className="text-sm">
                          {renderHighlighted(suburb.name, value)}
                        </span>
                        {suburb.region && (
                          <span className="ml-2 text-xs text-[#4A615A] font-normal hidden sm:inline">
                            · {suburb.region}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Postcode Pill Badge */}
                    {suburb.postcode && (
                      <span className="ml-3 shrink-0 px-2 py-0.5 rounded-full text-[11px] font-mono font-medium tracking-tight bg-[#E8EFEA] text-[#1A3A32] border border-[#1A3A32]/10">
                        {renderHighlighted(suburb.postcode, value)}
                      </span>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="p-4 text-center">
                <p className="text-xs font-semibold text-[#1A3A32]">No matching suburbs found</p>
                <p className="text-[11px] text-[#4A615A] mt-1">
                  DTD currently supports Greater Melbourne. Try searching with a 4-digit postcode or neighboring suburb.
                </p>
              </div>
            )}
          </div>

          {/* Micro Footer Hint */}
          <div className="px-4 py-1.5 bg-[#FAFAF7] border-t border-[#E5DFD3]/60 text-[10px] text-[#5C6D59] flex items-center justify-between">
            <span>Use ↑ ↓ keys to navigate</span>
            <span>↵ Enter to select</span>
          </div>
        </div>
      )}
    </div>
  );
}
