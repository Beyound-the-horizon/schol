import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { scholarships, type Scholarship } from "./data/scholarships";
import HomeView from "./assets/Views/homeView";
import ScholarshipView from "./assets/Views/scholarshipView";
import UserInformation from "./assets/Views/userInformation";
import Bookmarks from "./assets/Views/bookmarks";
import { Toaster } from "@/components/ui/sonner";
import type { Filters } from "./assets/Components/Search bar/searchbarItem";
import { deadlineToIso, filterScholarships } from "./lib/filterScholarships";
import { loadStoredAccount } from "./lib/googleAccount";
import { fetchScholarships, fetchScholarshipById } from "./services/api";
import { supabase } from "./lib/supabase";
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
  const [dbScholarships, setDbScholarships] = useState<Scholarship[]>([]);
  const [detailedScholarship, setDetailedScholarship] = useState<Scholarship | null>(null);
  const [stats, setStats] = useState({ ongoing: "4", eligible: "2", total: "6" });
  const [apiTotalPages, setApiTotalPages] = useState<number>(1);
  const screen = stack[stack.length - 1] ?? "home";

  const [pageSize, setPageSize] = useState(() => {
    if (typeof window === "undefined") return 10;
    const available = window.innerHeight - 170;
    return Math.max(5, Math.min(10, Math.floor(available / 48)));
  });

  useEffect(() => {
    function handleResize() {
      const available = window.innerHeight - 170;
      setPageSize(Math.max(5, Math.min(10, Math.floor(available / 48))));
    }
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Reusable loader for initial, filtered, and realtime updates
  const loadScholarships = useCallback(() => {
    fetchScholarships({
      page,
      limit: pageSize,
      location: filters.location,
      organization: filters.type,
      offer: filters.funding,
      status: filters.status,
      course: filters.course,
    })
      .then((res) => {
        if (res.scholarships && res.scholarships.length > 0) {
          setDbScholarships(res.scholarships);
          setApiTotalPages(res.totalPages || 1);
          setStats(res.stats);
        }
      })
      .catch((err) => {
        console.warn("Could not fetch scholarships from backend, using fallback:", err);
      });
  }, [page, pageSize, filters]);

  // Initial and filter-change fetch
  useEffect(() => {
    loadScholarships();
  }, [loadScholarships]);

  // Realtime subscription & focus refresh whenever entries are added/updated in Supabase
  useEffect(() => {
    // 1. Supabase Postgres changes listener (instant realtime push)
    const channel = supabase
      .channel("scholarships-realtime-feed")
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "scholarships",
        },
        () => {
          loadScholarships();
        }
      )
      .subscribe();

    // 2. Re-fetch when user focuses the tab after working in Supabase Table Editor
    function onTabFocus() {
      loadScholarships();
    }
    window.addEventListener("focus", onTabFocus);
    document.addEventListener("visibilitychange", onTabFocus);

    // 3. Periodic polling interval (every 10 seconds)
    const interval = setInterval(loadScholarships, 10000);

    return () => {
      supabase.removeChannel(channel);
      window.removeEventListener("focus", onTabFocus);
      document.removeEventListener("visibilitychange", onTabFocus);
      clearInterval(interval);
    };
  }, [loadScholarships]);

  const activeScholarships = useMemo(
    () => (dbScholarships.length > 0 ? dbScholarships : scholarships),
    [dbScholarships]
  );

  const selected = useMemo(() => {
    if (detailedScholarship && detailedScholarship.id === selectedId) {
      return detailedScholarship;
    }
    return (
      activeScholarships.find((item) => item.id === selectedId) ??
      activeScholarships[0] ??
      scholarships[0]
    );
  }, [selectedId, detailedScholarship, activeScholarships]);

  const visibleScholarships = useMemo(() => {
    if (dbScholarships.length > 0) {
      return dbScholarships;
    }
    return filterScholarships(scholarships, filters);
  }, [dbScholarships, filters]);

  const pageScholarships = useMemo(() => {
    if (dbScholarships.length > 0) {
      return dbScholarships;
    }
    const total = visibleScholarships.length;
    if (total === 0) return [];
    const startIndex = ((page - 1) * pageSize) % total;
    const result: typeof visibleScholarships = [];
    for (let i = 0; i < pageSize; i++) {
      const item = visibleScholarships[(startIndex + i) % total];
      if (item) {
        result.push(item);
      }
    }
    return result;
  }, [dbScholarships, visibleScholarships, page, pageSize]);

  const bookmarkedScholarships = useMemo(
    () =>
      bookmarkedIds
        .map(
          (id) =>
            activeScholarships.find((item) => item.id === id) ??
            scholarships.find((item) => item.id === id)
        )
        .filter((item): item is (typeof scholarships)[number] => Boolean(item)),
    [bookmarkedIds, activeScholarships]
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

  async function openScholarship(id: number, source: ScholarshipSource = "home") {
    setSelectedId(id);
    setScholarshipSource(source);
    setSearchOpen(false);
    navigate("scholarship");

    try {
      const detailed = await fetchScholarshipById(id);
      if (detailed) {
        setDetailedScholarship(detailed);
      }
    } catch (err) {
      console.warn("Could not fetch detailed scholarship by ID:", err);
    }
  }

  function toggleBookmark(id: number) {
    const exists = bookmarkedIds.includes(id);
    const name =
      activeScholarships.find((item) => item.id === id)?.name ??
      scholarships.find((item) => item.id === id)?.name ??
      "Scholarship";
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
        setPage((current) => Math.min(apiTotalPages, current + 1));
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [screen, searchOpen, apiTotalPages]);

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
          scholarships={activeScholarships}
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
          totalPages={apiTotalPages}
          ongoingCount={stats.ongoing}
          eligibleCount={stats.eligible}
          totalCount={stats.total}
          onSelectScholarship={(id) => openScholarship(id, "home")}
          onPrevPage={() => setPage((current) => Math.max(1, current - 1))}
          onNextPage={() => setPage((current) => Math.min(apiTotalPages, current + 1))}
          onGoToPage={setPage}
          {...sharedNav}
        />
      )}
    </>
  );
}
