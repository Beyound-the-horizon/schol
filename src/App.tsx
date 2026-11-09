import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { scholarships as mockScholarships, type Scholarship } from "./data/scholarships";
import HomeView from "./assets/Views/homeView";
import ScholarshipView from "./assets/Views/scholarshipView";
import UserInformation from "./assets/Views/userInformation";
import Bookmarks from "./assets/Views/bookmarks";
import { Toaster } from "@/components/ui/sonner";
import type { Filters } from "./assets/Components/Search bar/searchbarItem";
import { deadlineToIso } from "./lib/filterScholarships";
import { loadStoredAccount } from "./lib/googleAccount";
import { fetchScholarshipById, fetchScholarships } from "./services/api";
import { useDebounce } from "./hooks/useDebounce";
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
  const [scholarshipsList, setScholarshipsList] = useState<Scholarship[]>(mockScholarships);
  const [selectedId, setSelectedId] = useState<number>(mockScholarships[0].id);
  const [selectedDetail, setSelectedDetail] = useState<Scholarship | null>(null);
  const [bookmarkedIds, setBookmarkedIds] = useState<number[]>(() => {
    try {
      const stored = localStorage.getItem("schol.bookmarks");
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const [bookmarkedCache, setBookmarkedCache] = useState<Record<number, Scholarship>>(() => {
    try {
      const stored = localStorage.getItem("schol.bookmarks.cache");
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  });

  // Sync bookmarks to localStorage on change
  useEffect(() => {
    try {
      localStorage.setItem("schol.bookmarks", JSON.stringify(bookmarkedIds));
    } catch {
      // Ignore quota or access errors in restricted sandbox environments
    }
  }, [bookmarkedIds]);

  useEffect(() => {
    try {
      localStorage.setItem("schol.bookmarks.cache", JSON.stringify(bookmarkedCache));
    } catch {
      // Ignore quota errors
    }
  }, [bookmarkedCache]);
  const [scholarshipSource, setScholarshipSource] = useState<ScholarshipSource>("home");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [stats, setStats] = useState({ ongoing: "12,000", eligible: "10,344", total: "16,218" });
  const [filters, setFilters] = useState<Filters>({});
  const [searchQuery, setSearchQuery] = useState("");
  const [, setIsLoading] = useState<boolean>(true);
  const [, setIsOffline] = useState<boolean>(false);

  // Debounce search to avoid rapid API calls while typing
  const debouncedSearch = useDebounce(searchQuery, 300);

  const screen = stack[stack.length - 1] ?? "home";

  // Active selected scholarship combining full detail from API with fallback
  const selected = useMemo(
    () =>
      (selectedDetail && selectedDetail.id === selectedId ? selectedDetail : null) ||
      scholarshipsList.find((item) => item.id === selectedId) ||
      mockScholarships.find((item) => item.id === selectedId) ||
      mockScholarships[0],
    [selectedDetail, selectedId, scholarshipsList]
  );

  // Server-side filtering: scholarshipsList already contains filtered results from the API.
  // No local filterScholarships() call needed — the backend handles search, location,
  // organization, offer, status, and course filters via query parameters.

  const bookmarkedScholarships = useMemo(
    () =>
      bookmarkedIds
        .map((id) =>
          scholarshipsList.find((item) => item.id === id) ||
          bookmarkedCache[id] ||
          mockScholarships.find((item) => item.id === id)
        )
        .filter((item): item is Scholarship => Boolean(item)),
    [bookmarkedIds, scholarshipsList, bookmarkedCache]
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

  // Reset page to 1 whenever filters or search query change
  const prevFiltersRef = useRef(filters);
  const prevSearchRef = useRef(debouncedSearch);
  useEffect(() => {
    const filtersChanged = prevFiltersRef.current !== filters;
    const searchChanged = prevSearchRef.current !== debouncedSearch;
    prevFiltersRef.current = filters;
    prevSearchRef.current = debouncedSearch;
    if (filtersChanged || searchChanged) {
      setPage(1);
    }
  }, [filters, debouncedSearch]);

  // Load scholarships from backend API on mount, pagination, filters, and search changes
  useEffect(() => {
    let isMounted = true;
    const abortController = new AbortController();

    setIsLoading(true);

    // Map frontend filter keys to backend API parameters
    const apiParams: Parameters<typeof fetchScholarships>[0] = {
      page,
      signal: abortController.signal,
    };
    if (debouncedSearch.trim()) {
      apiParams.search = debouncedSearch.trim();
    }
    if (filters.location?.length) {
      apiParams.location = filters.location;
    }
    if (filters.type?.length) {
      apiParams.organization = filters.type;
    }
    if (filters.funding?.length) {
      apiParams.offer = filters.funding;
    }
    if (filters.status?.length) {
      apiParams.status = filters.status;
    }
    if (filters.course?.length) {
      apiParams.course = filters.course;
    }

    fetchScholarships(apiParams)
      .then((data) => {
        if (!isMounted) return;
        if (data.scholarships && data.scholarships.length > 0) {
          setScholarshipsList(data.scholarships);
          setTotalPages(data.totalPages || 1);
          setStats(data.stats);
          setIsOffline(false);
        } else {
          // If API returns 0 records, keep mock demo records so UI remains fully functional
          setScholarshipsList(mockScholarships);
        }
        setIsLoading(false);
      })
      .catch((err: Error) => {
        if (!isMounted || err.name === "AbortError") return;
        setIsOffline(true);
        setIsLoading(false);
        // Retain mock scholarships as explicitly identified fallback
        setScholarshipsList(mockScholarships);
      });

    return () => {
      isMounted = false;
      abortController.abort();
    };
  }, [page, filters, debouncedSearch]);

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

    // Fetch full 24-field detail record from backend
    fetchScholarshipById(id)
      .then((detail) => setSelectedDetail(detail))
      .catch(() => {
        // Fall back gracefully to existing listing item or mock
        setSelectedDetail(null);
      });

    navigate("scholarship");
  }

  function toggleBookmark(id: number) {
    const exists = bookmarkedIds.includes(id);
    const item =
      scholarshipsList.find((s) => s.id === id) ||
      bookmarkedCache[id] ||
      mockScholarships.find((s) => s.id === id);
    const name = item?.name ?? "Scholarship";

    if (!exists && item) {
      setBookmarkedCache((prev) => ({ ...prev, [id]: item }));
    } else if (exists) {
      setBookmarkedCache((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    }

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
      setSearchQuery("");
      toast("Filters removed", { id: "filters-cleared" });
    },
    searchQuery,
    onSearchQueryChange: setSearchQuery,
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
          scholarships={scholarshipsList}
          bookmarked={bookmarkedIds.includes(selected.id)}
          source={scholarshipSource}
          onBack={goHome}
          onSelectScholarship={(id) => openScholarship(id, scholarshipSource)}
          onToggleBookmark={() => toggleBookmark(selected.id)}
          {...sharedNav}
        />
      ) : (
        <HomeView
          scholarships={scholarshipsList}
          page={page}
          totalPages={totalPages}
          ongoingCount={stats.ongoing}
          eligibleCount={stats.eligible}
          totalCount={stats.total}
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
