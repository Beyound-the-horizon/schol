/**
 * Centralized API Client for Scholarship Platform
 * Connects frontend React components to the FastAPI backend service.
 */

import type { DocumentRequirement, Scholarship, ScholarshipKind } from "../data/scholarships";

// Base API URL configured via Vite environment variable, defaulting to local FastAPI service
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

/**
 * Backend scholarship record matching public API contract.
 */
export type ApiScholarship = {
  id: number;
  name: string;
  location: string;
  organization: string;
  offer: string;
  eligibility: string;
  deadline: string | null;
  display_deadline?: string | null;
  source?: string | null;
  official_url?: string | null;
  deadlineDate?: string | null;
  daysLeft?: string | null;
  eligibilityDetail?: string | null;
  duration?: string | null;
  minCgpa?: string | null;
  workExperience?: string | null;
  recommendations?: string | null;
  english?: string | null;
  documents?: string | null;
  documentRequirements?: DocumentRequirement[] | null;
  motivation?: string | null;
  stipend?: string | null;
  benefits?: string[] | null;
  courses?: string[] | null;
  focusAreas?: string[] | null;
  selection?: string | null;
};

export type ApiScholarshipListResponse = {
  items: ApiScholarship[];
  pagination: {
    page: number;
    limit: number;
    total_records: number;
    total_pages: number;
  };
  stats: {
    total_count: string;
    ongoing_count: string;
    eligible_count: string;
  };
};

/**
 * Safely casts an arbitrary organization string to the frontend's ScholarshipKind union.
 */
export function normalizeOrganization(kind?: string | null): ScholarshipKind {
  const valid: ScholarshipKind[] = ["Institution", "Organization", "Foundation", "Government"];
  if (kind && (valid as string[]).includes(kind)) {
    return kind as ScholarshipKind;
  }
  return "Organization";
}

/**
 * Formats an ISO 8601 calendar date (YYYY-MM-DD) into a user-friendly display string.
 */
export function formatDeadlineDisplay(deadline: string | null): string {
  if (!deadline) {
    return "Rolling / Open";
  }

  try {
    const [year, month, day] = deadline.split("-").map(Number);
    if (!year || !month || !day) return deadline;

    const dateObj = new Date(year, month - 1, day);
    if (isNaN(dateObj.getTime())) return deadline;

    return dateObj.toLocaleDateString("en-US", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return deadline;
  }
}

/**
 * Maps raw backend API record to the UI's Scholarship interface.
 */
export function mapApiToUiScholarship(item: ApiScholarship): Scholarship {
  return {
    id: item.id,
    name: item.name,
    location: item.location,
    organization: normalizeOrganization(item.organization),
    offer: item.offer,
    eligibility: item.eligibility,
    deadline: item.display_deadline || (item.deadline ? formatDeadlineDisplay(item.deadline) : "Rolling / Open"),
    source: item.source || (item.official_url ? "Url" : undefined),
    official_url: item.official_url || undefined,
    deadlineDate: item.deadlineDate || (item.deadline ? formatDeadlineDisplay(item.deadline) : "Rolling / Open"),
    daysLeft: item.daysLeft || undefined,
    eligibilityDetail: item.eligibilityDetail || undefined,
    duration: item.duration || undefined,
    minCgpa: item.minCgpa || undefined,
    workExperience: item.workExperience || undefined,
    recommendations: item.recommendations || undefined,
    english: item.english || undefined,
    documents: item.documents || undefined,
    documentRequirements: item.documentRequirements || undefined,
    motivation: item.motivation || undefined,
    stipend: item.stipend || undefined,
    benefits: item.benefits || undefined,
    courses: item.courses || undefined,
    focusAreas: item.focusAreas || undefined,
    selection: item.selection || undefined,
  };
}

export type FetchScholarshipsParams = {
  page?: number;
  limit?: number;
  search?: string;
  location?: string | string[];
  organization?: string | string[];
  offer?: string | string[];
  status?: string | string[];
  course?: string | string[];
  signal?: AbortSignal;
};

/**
 * Fetch published scholarships from the backend.
 * Returns the full response envelope containing items, pagination, and dashboard stats.
 */
export async function fetchScholarships(
  params: FetchScholarshipsParams = {}
): Promise<{
  scholarships: Scholarship[];
  totalPages: number;
  totalRecords: number;
  stats: { ongoing: string; eligible: string; total: string };
}> {
  const query = new URLSearchParams();
  query.set("envelope", "true");
  if (params.page) query.set("page", String(params.page));
  if (params.limit) query.set("limit", String(params.limit));
  if (params.search && params.search.trim()) query.set("search", params.search.trim());

  if (params.location) {
    const val = Array.isArray(params.location) ? params.location.join(",") : params.location;
    if (val.trim()) query.set("location", val.trim());
  }
  if (params.organization) {
    const val = Array.isArray(params.organization) ? params.organization.join(",") : params.organization;
    if (val.trim()) query.set("organization", val.trim());
  }
  if (params.offer) {
    const val = Array.isArray(params.offer) ? params.offer.join(",") : params.offer;
    if (val.trim()) query.set("offer", val.trim());
  }
  if (params.status) {
    const val = Array.isArray(params.status) ? params.status.join(",") : params.status;
    if (val.trim()) query.set("status", val.trim());
  }
  if (params.course) {
    const val = Array.isArray(params.course) ? params.course.join(",") : params.course;
    if (val.trim()) query.set("course", val.trim());
  }

  const response = await fetch(`${API_BASE_URL}/scholarships?${query.toString()}`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    signal: params.signal,
  });

  if (!response.ok) {
    throw new Error(
      `Failed to retrieve scholarships: HTTP ${response.status} ${response.statusText}`
    );
  }

  const data: ApiScholarshipListResponse = await response.json();
  return {
    scholarships: (data.items || []).map(mapApiToUiScholarship),
    totalPages: data.pagination?.total_pages || 1,
    totalRecords: data.pagination?.total_records || 0,
    stats: {
      ongoing: data.stats?.ongoing_count || "0",
      eligible: data.stats?.eligible_count || "0",
      total: data.stats?.total_count || "0",
    },
  };
}

/**
 * Fetch detailed scholarship by ID from backend.
 */
export async function fetchScholarshipById(
  id: number | string,
  signal?: AbortSignal
): Promise<Scholarship> {
  const response = await fetch(`${API_BASE_URL}/scholarships/${id}`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error(
      `Scholarship #${id} not found or unavailable (HTTP ${response.status})`
    );
  }

  const rawItem: ApiScholarship = await response.json();
  return mapApiToUiScholarship(rawItem);
}
