import { Bookmark, User } from "lucide-react";
import IconItem from "../Icon item/iconItem";
import SearchbarItem, { type Filters } from "../Search bar/searchbarItem";
import type { Scholarship } from "../../../data/scholarships";
import "./topBar.css";

type TopBarProps = {
  scholarships: Scholarship[];
  searchOpen: boolean;
  onOpenSearch: () => void;
  onCloseSearch: () => void;
  onSelectScholarship: (id: number) => void;
  onOpenProfile: () => void;
  onOpenBookmarks: () => void;
  filters?: Filters;
  onFiltersChange?: (filters: Filters) => void;
  onClearFilters?: () => void;
};

export default function TopBar({
  scholarships,
  searchOpen,
  onOpenSearch,
  onCloseSearch,
  onSelectScholarship,
  onOpenProfile,
  onOpenBookmarks,
  filters,
  onFiltersChange,
  onClearFilters,
}: TopBarProps) {
  return (
    <header className="topBar">
      <div className="topBarInner">
        <SearchbarItem
          scholarships={scholarships}
          collapsed
          onOpen={onOpenSearch}
          filters={filters}
          onFiltersChange={onFiltersChange}
        />
        <div className="topBarActions">
          <IconItem
            size={32}
            icon={<User size={14} strokeWidth={1.5} />}
            aria-label="User information"
            onClick={onOpenProfile}
          />
          <IconItem
            size={32}
            icon={<Bookmark size={14} strokeWidth={1.5} />}
            aria-label="Bookmarks"
            onClick={onOpenBookmarks}
          />
        </div>
      </div>

      {searchOpen ? (
        <>
          <button
            type="button"
            className="searchBackdrop"
            aria-label="Dismiss search"
            onClick={onCloseSearch}
          />
          <div className="searchOverlay">
            <SearchbarItem
              scholarships={scholarships}
              collapsed={false}
              onClose={onCloseSearch}
              onSelectScholarship={onSelectScholarship}
              filters={filters}
              onFiltersChange={onFiltersChange}
              onClearFilters={onClearFilters}
            />
          </div>
        </>
      ) : null}
    </header>
  );
}
