import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { scholarships } from "./data/scholarships";
import HomeView from "./assets/Views/homeView";
import ScholarshipView from "./assets/Views/scholarshipView";
import UserInformation from "./assets/Views/userInformation";
import Bookmarks from "./assets/Views/bookmarks";
import { Toaster } from "@/components/ui/sonner";
import type { Filters } from "./assets/Components/Search bar/searchbarItem";
import { deadlineToIso, filterScholarships } from "./lib/filterScholarships";
import { loadStoredAccount } from "./lib/googleAccount";
import "./App.css";

type Screen = "home" | "scholarship" | "profile" | "bookmarks";
type ScholarshipSource = "home" | "bookmarks";

function isTypingTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.tagName === "INPUT" ||
    target.tagName === "TEXTAREA" ||
    target.isContentEditable
  );
}

export default function App() {
  const [stack, setStack] = useState<Screen[]>(["home"]);
  const [searchOpen, setSearchOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<number>(scholarships[0].id);
  const [bookmarkedIds, setBookmarkedIds] = useState<number[]>([]);
  const [scholarshipSource, setScholarshipSource] =
    useState<ScholarshipSource>("home");
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<Filters>({});
  const totalPages = 3056;
  const screen = stack[stack.length - 1] ?? "home";

  const selected = useMemo(
    () => scholarships.find((item) => item.id === selectedId) ?? scholarships[0],
    [selectedId]
  );

  const visibleScholarships = useMemo(
    () => filterScholarships(scholarships, filters),
    [filters]
  );

  const PAGE_SIZE = 10;
  const pageScholarships = useMemo(() => {
    const total = visibleScholarships.length;
    if (total === 0) return [];
    const startIndex = ((page - 1) * PAGE_SIZE) % total;
    const result: typeof visibleScholarships = [];
    for (let i = 0; i < PAGE_SIZE; i++) {
      const item = visibleScholarships[(startIndex + i) % total];
      if (item) {
        result.push(item);
      }
    }
    return result;
  }, [visibleScholarships, page]);

  const bookmarkedScholarships = useMemo(
    () =>
      bookmarkedIds
        .map((id) => scholarships.find((item) => item.id === id))
        .filter((item): item is (typeof scholarships)[number] => Boolean(item)),
    [bookmarkedIds]
  );

  const calendarEvents = useMemo(
    () =>
      bookmarkedScholarships
        .map((item) => {
          const date = deadlineToIso(item.deadlineDate);
          return date ? { title: `${item.name} deadline`, date } : null;
        })
        .filter((item): item is { title: string; date: string } => Boolean(item)),
    [bookmarkedScholarships]
  );

  function navigate(next: Screen) {
    setStack((current) =>
      current[current.length - 1] === next ? current : [...current, next]
    );
  }

  function goBack() {
    setSearchOpen(false);
    setStack((current) => (current.length > 1 ? current.slice(0, -1) : ["home"]));
  }

  function goHome() {
    setSearchOpen(false);
    setStack(["home"]);
  }

  function openScholarship(id: number, source: ScholarshipSource = "home") {
    setSelectedId(id);
    setScholarshipSource(source);
    setSearchOpen(false);
    navigate("scholarship");
  }

  function toggleBookmark(id: number) {
    const exists = bookmarkedIds.includes(id);
    const name =
      scholarships.find((item) => item.id === id)?.name ?? "Scholarship";
    setBookmarkedIds((current) =>
      exists ? current.filter((item) => item !== id) : [...current, id]
    );
    toast(exists ? "Bookmark removed" : "Scholarship bookmarked", {
      id: `bookmark-${id}`,
    });
    if (!exists && loadStoredAccount() && Notification.permission === "granted") {
      new Notification("Scholarship bookmarked", { body: name });
    }
  }

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        if (searchOpen) {
          setSearchOpen(false);
          return;
        }
        if (screen !== "home") goBack();
        return;
      }

      if (isTypingTarget(event.target)) return;

      if (event.key === "/" || ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k")) {
        event.preventDefault();
        setSearchOpen(true);
        return;
      }

      if (screen !== "home") return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        setPage((current) => Math.max(1, current - 1));
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        setPage((current) => Math.min(totalPages, current + 1));
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [screen, searchOpen, totalPages]);

  const sharedNav = {
    searchOpen,
    onOpenSearch: () => setSearchOpen(true),
    onCloseSearch: () => setSearchOpen(false),
    onOpenProfile: () => navigate("profile"),
    onOpenBookmarks: () => navigate("bookmarks"),
    filters,
    onFiltersChange: setFilters,
    onClearFilters: () => {
      setFilters({});
      toast("Filters removed", { id: "filters-cleared" });
    },
  };

  return (
    <>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            borderRadius: 0,
            boxShadow: "none",
            border: "1px solid var(--color-border-primary)",
            background: "var(--bg-base-color-light)",
            color: "var(--text-color-secondary)",
            fontFamily: "var(--rowitem-font)",
            fontSize: "13px",
          },
        }}
      />

      {screen === "profile" ? (
        <UserInformation onClose={goBack} calendarEvents={calendarEvents} />
      ) : screen === "bookmarks" ? (
        <Bookmarks
          scholarships={bookmarkedScholarships}
          onClose={goBack}
          onOpenScholarship={(id) => openScholarship(id, "bookmarks")}
          onRemove={toggleBookmark}
        />
      ) : screen === "scholarship" ? (
        <ScholarshipView
          scholarship={selected}
          scholarships={scholarships}
          bookmarked={bookmarkedIds.includes(selected.id)}
          source={scholarshipSource}
          onBack={goHome}
          onSelectScholarship={(id) => openScholarship(id, scholarshipSource)}
          onToggleBookmark={() => toggleBookmark(selected.id)}
          {...sharedNav}
        />
      ) : (
        <HomeView
          scholarships={pageScholarships}
          page={page}
          totalPages={totalPages}
          ongoingCount="12,000"
          eligibleCount="10,344"
          totalCount="16,218"
          onSelectScholarship={(id) => openScholarship(id, "home")}
          onPrevPage={() => setPage((current) => Math.max(1, current - 1))}
          onNextPage={() => setPage((current) => Math.min(totalPages, current + 1))}
          onGoToPage={setPage}
          {...sharedNav}
        />
      )}
    </>
  );
}
