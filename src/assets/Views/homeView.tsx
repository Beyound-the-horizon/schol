import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import ButtonItem from "../Components/Button item/buttonItem";
import IconItem from "../Components/Icon item/iconItem";
import FieldItem from "../Components/Field item/fieldItem";
import TopBar from "../Components/Top bar/topBar";
import ScholarshipList from "../Components/Scholarship List/scholarshipList";
import type { Filters } from "../Components/Search bar/searchbarItem";
import type { Scholarship } from "../../data/scholarships";
import "./homeView.css";

type HomeViewProps = {
  scholarships: Scholarship[];
  searchOpen: boolean;
  page: number;
  totalPages: number;
  ongoingCount: string;
  eligibleCount: string;
  totalCount: string;
  onOpenSearch: () => void;
  onCloseSearch: () => void;
  onSelectScholarship: (id: number) => void;
  onOpenProfile: () => void;
  onOpenBookmarks: () => void;
  onPrevPage: () => void;
  onNextPage: () => void;
  onGoToPage: (page: number) => void;
  filters?: Filters;
  onFiltersChange?: (filters: Filters) => void;
  onClearFilters?: () => void;
};

export default function HomeView({
  scholarships,
  searchOpen,
  page,
  totalPages,
  ongoingCount,
  eligibleCount,
  totalCount,
  onOpenSearch,
  onCloseSearch,
  onSelectScholarship,
  onOpenProfile,
  onOpenBookmarks,
  onPrevPage,
  onNextPage,
  onGoToPage,
  filters,
  onFiltersChange,
  onClearFilters,
}: HomeViewProps) {
  const [pageDraft, setPageDraft] = useState(String(page));

  useEffect(() => {
    setPageDraft(String(page));
  }, [page]);

  function commitPage() {
    const next = Number.parseInt(pageDraft, 10);
    if (Number.isNaN(next)) {
      setPageDraft(String(page));
      return;
    }
    onGoToPage(Math.min(totalPages, Math.max(1, next)));
  }

  return (
    <div className="homeView">
      <TopBar
        scholarships={scholarships}
        searchOpen={searchOpen}
        onOpenSearch={onOpenSearch}
        onCloseSearch={onCloseSearch}
        onSelectScholarship={onSelectScholarship}
        onOpenProfile={onOpenProfile}
        onOpenBookmarks={onOpenBookmarks}
        filters={filters}
        onFiltersChange={onFiltersChange}
        onClearFilters={onClearFilters}
      />

      <section className="homeContent">
        <div className="listToolbar">
          <div className="pagination">
            <IconItem
              size={32}
              icon={<ChevronLeft size={14} strokeWidth={1.5} />}
              aria-label="Previous page"
              onClick={onPrevPage}
            />
            <div className="pageRange">
              <FieldItem
                className="pageInput"
                size={24}
                tone="value"
                inputMode="numeric"
                aria-label="Go to page"
                value={pageDraft}
                onChange={(event) => setPageDraft(event.target.value)}
                onBlur={commitPage}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    commitPage();
                  }
                }}
              />
              <span className="pageDivider">/</span>
              <span className="pageTotal">{totalPages}</span>
            </div>
            <IconItem
              size={32}
              icon={<ChevronRight size={14} strokeWidth={1.5} />}
              aria-label="Next page"
              onClick={onNextPage}
            />
          </div>

          <div className="listStats">
            <div className="stat">
              <ButtonItem size={24} interactive={false} text={ongoingCount} />
              <span>Ongoing</span>
            </div>
            <div className="stat">
              <ButtonItem size={24} interactive={false} text={eligibleCount} />
              <span>Eligible</span>
            </div>
            <div className="stat">
              <ButtonItem size={24} interactive={false} text={totalCount} />
              <span>Total</span>
            </div>
          </div>
        </div>

        <ScholarshipList
          scholarships={scholarships}
          onSelect={onSelectScholarship}
        />
      </section>
    </div>
  );
}
