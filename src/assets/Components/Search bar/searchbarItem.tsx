import { useEffect, useMemo, useState } from "react";
import {
  BadgeCheck,
  Banknote,
  BookOpen,
  Check,
  CircleDot,
  MapPin,
  Search,
  User,
  X,
} from "lucide-react";
import ShortcutBar from "../Shortcut bar/shortcutBar";
import ButtonItem from "../Button item/buttonItem";
import IconItem from "../Icon item/iconItem";
import FieldItem from "../Field item/fieldItem";
import { courseOptions, type Scholarship } from "../../../data/scholarships";
import "./searchbaritem.css";

export type FilterKey =
  | "eligibility"
  | "type"
  | "funding"
  | "location"
  | "course"
  | "status";

export type Filters = Partial<Record<FilterKey, string[]>>;

type SearchbarItemProps = {
  scholarships: Scholarship[];
  collapsed?: boolean;
  onOpen?: () => void;
  onClose?: () => void;
  onSelectScholarship?: (id: number) => void;
  filters?: Filters;
  onFiltersChange?: (filters: Filters) => void;
  onClearFilters?: () => void;
};

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "eligibility", label: "Eligibility" },
  { key: "type", label: "Type" },
  { key: "funding", label: "Funding" },
  { key: "location", label: "Location" },
  { key: "course", label: "Course" },
  { key: "status", label: "Status" },
];

const OPTIONS: Record<FilterKey, string[]> = {
  eligibility: ["Eligible", "Ineligible"],
  type: ["Organization", "Foundation", "Institution", "Government"],
  funding: ["Fully-funded", "Partial"],
  location: [
    "India",
    "Spain",
    "Sweden",
    "Japan",
    "Russia",
    "Italy",
    "United States",
    "China",
    "Germany",
    "United Kingdom",
    "Algeria",
    "Nigeria",
  ],
  course: courseOptions,
  status: ["Ongoing", "Closed"],
};

function FilterIcon({ name }: { name: FilterKey | "clear" }) {
  const props = { size: 14, strokeWidth: 1.5 };
  if (name === "eligibility") return <BadgeCheck {...props} />;
  if (name === "type" || name === "clear") return <User {...props} />;
  if (name === "funding") return <Banknote {...props} />;
  if (name === "status") return <CircleDot {...props} />;
  if (name === "course") return <BookOpen {...props} />;
  return <MapPin {...props} />;
}

type SearchableFilterProps = {
  filter: "location" | "course";
  query: string;
  onQueryChange: (value: string) => void;
  selectedValues: string[];
  options: string[];
  onToggle: (value: string) => void;
};

function SearchableFilter({
  filter,
  query,
  onQueryChange,
  selectedValues,
  options,
  onToggle,
}: SearchableFilterProps) {
  const suggestion = options.find((item) =>
    item.toLowerCase().startsWith(query.trim().toLowerCase())
  );
  const matches = options.filter((item) =>
    item.toLowerCase().includes(query.trim().toLowerCase())
  );

  return (
    <div className="locationFilter">
      <div className="locationSearch">
        {query && suggestion ? (
          <span className="locationGhost" aria-hidden="true">
            <span className="locationGhostTyped">{query}</span>
            <span className="locationGhostRest">
              {suggestion.slice(query.length)}
            </span>
          </span>
        ) : null}
        <FieldItem
          size={32}
          placeholder="Search"
          value={query}
          aria-label={filter === "course" ? "Search courses" : "Search locations"}
          aria-autocomplete="list"
          onChange={(event) => onQueryChange(event.target.value)}
          onKeyDown={(event) => {
            if ((event.key === "Tab" || event.key === "Enter") && query && suggestion) {
              event.preventDefault();
              onQueryChange(suggestion);
              if (!selectedValues.includes(suggestion)) onToggle(suggestion);
            }
          }}
        />
      </div>
      {selectedValues.length > 0 && (
        <div className="locationChips" role="list" aria-label="Selected filters">
          {selectedValues.map((value) => (
            <button
              key={value}
              type="button"
              className="locationChip"
              role="listitem"
              aria-label={`Remove filter: ${value}`}
              onClick={() => onToggle(value)}
            >
              <span>{value}</span>
              <X size={12} strokeWidth={1.5} className="chipCloseIcon" />
            </button>
          ))}
        </div>
      )}
      <div className={filter === "course" ? "locationGrid courseGrid" : "locationGrid"}>
        {(query ? matches : options).map((value) => (
          <ButtonItem
            key={value}
            size={28}
            className="filterPick"
            text={value}
            state={selectedValues.includes(value) ? "active" : "default"}
            onClick={() => {
              onToggle(value);
              onQueryChange("");
            }}
          />
        ))}
      </div>
    </div>
  );
}

export default function searchbarItem({
  scholarships,
  collapsed = true,
  onOpen,
  onClose,
  onSelectScholarship,
  filters,
  onFiltersChange,
  onClearFilters,
}: SearchbarItemProps) {
  const [query, setQuery] = useState("");
  const [locationQuery, setLocationQuery] = useState("");
  const [courseQuery, setCourseQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<FilterKey>("eligibility");
  const [internalFilters, setInternalFilters] = useState<Filters>({});
  const selected = filters ?? internalFilters;

  function setSelected(next: Filters | ((current: Filters) => Filters)) {
    const resolved = typeof next === "function" ? next(selected) : next;
    onFiltersChange?.(resolved);
    if (!filters) setInternalFilters(resolved);
  }

  const selectedLocations = selected.location ?? [];
  const selectedCourses = selected.course ?? [];

  useEffect(() => {
    if (collapsed) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose?.();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [collapsed, onClose]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return scholarships.filter((item) =>
      `${item.name} ${item.location} ${item.organization} ${(item.courses ?? []).join(" ")} ${(item.focusAreas ?? []).join(" ")}`
        .toLowerCase()
        .includes(q)
    );
  }, [query, scholarships]);

  function toggleOption(filter: FilterKey, value: string) {
    setSelected((current) => {
      const existing = current[filter] ?? [];
      const next = existing.includes(value)
        ? existing.filter((item) => item !== value)
        : [...existing, value];
      return { ...current, [filter]: next };
    });
  }

  if (collapsed) {
    return (
      <ButtonItem
        className="searchTrigger"
        size={32}
        text="Search for scholarships..."
        LeftIcon={<Search size={14} strokeWidth={2} />}
        onClick={onOpen}
      />
    );
  }

  return (
    <div className="searchPanel">
      <div className="searchPanelHeader">
        <FieldItem
          size={32}
          tone="placeholder"
          className="searchInput"
          placeholder="Search for scholarships..."
          value={query}
          autoFocus
          onChange={(event) => setQuery(event.target.value)}
        />
        <IconItem
          size={32}
          icon={<X size={14} strokeWidth={2} />}
          aria-label="Close search"
          onClick={onClose}
        />
      </div>

      {query.trim() ? (
        <div className="searchResults">
          {results.length === 0 ? (
            <p className="searchEmpty">No matching scholarships</p>
          ) : (
            results.map((item) => (
              <button
                key={item.id}
                type="button"
                className="searchResultRow"
                onClick={() => onSelectScholarship?.(item.id)}
              >
                {item.name}
              </button>
            ))
          )}
        </div>
      ) : (
        <div className="searchBody">
          <div className="searchFilters">
            {FILTERS.map((filter) => (
              <ButtonItem
                key={filter.key}
                size={28}
                text={filter.label}
                state={activeFilter === filter.key ? "active" : "default"}
                LeftIcon={<FilterIcon name={filter.key} />}
                onClick={() => setActiveFilter(filter.key)}
              />
            ))}
            <ButtonItem
              size={28}
              text="Remove filters"
              LeftIcon={<FilterIcon name="clear" />}
              onClick={() => {
                setSelected({});
                onClearFilters?.();
              }}
            />
          </div>

          {activeFilter === "location" ? (
            <SearchableFilter
              filter="location"
              query={locationQuery}
              onQueryChange={setLocationQuery}
              selectedValues={selectedLocations}
              options={OPTIONS.location}
              onToggle={(value) => toggleOption("location", value)}
            />
          ) : activeFilter === "course" ? (
            <SearchableFilter
              filter="course"
              query={courseQuery}
              onQueryChange={setCourseQuery}
              selectedValues={selectedCourses}
              options={OPTIONS.course}
              onToggle={(value) => toggleOption("course", value)}
            />
          ) : (
            <div className="filterOptions">
              {OPTIONS[activeFilter].map((option) => {
                const active = (selected[activeFilter] ?? []).includes(option);
                return (
                  <button
                    key={option}
                    type="button"
                    className="filterOption"
                    aria-pressed={active}
                    data-state={active ? "active" : "default"}
                    onClick={() => toggleOption(activeFilter, option)}
                  >
                    <span>{option}</span>
                    {active ? <Check size={14} strokeWidth={1.5} /> : null}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      <ShortcutBar
        placement="embedded"
        hints={[
          { label: "Previous page", keys: ["←"] },
          { label: "Next page", keys: ["→"] },
          { label: "Search", keys: ["/"] },
          { label: "Close", keys: ["Esc"] },
        ]}
      />
    </div>
  );
}
