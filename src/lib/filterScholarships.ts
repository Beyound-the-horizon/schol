import type { Filters } from "../assets/Components/Search bar/searchbarItem";
import type { Scholarship } from "../data/scholarships";

export function filterScholarships(
  scholarships: Scholarship[],
  filters: Filters
) {
  return scholarships.filter((item) => {
    const eligibility = filters.eligibility ?? [];
    if (eligibility.length) {
      const eligible = item.eligibility === "Eligible";
      const wantsEligible = eligibility.includes("Eligible");
      const wantsIneligible = eligibility.includes("Ineligible");
      if (eligible && !wantsEligible) return false;
      if (!eligible && !wantsIneligible) return false;
    }

    const types = filters.type ?? [];
    if (types.length && !types.includes(item.organization)) return false;

    const funding = filters.funding ?? [];
    if (funding.length && !funding.includes(item.offer)) return false;

    const locations = filters.location ?? [];
    if (
      locations.length &&
      !locations.some((place) =>
        item.location.toLowerCase().includes(place.toLowerCase())
      )
    ) {
      return false;
    }

    const courses = filters.course ?? [];
    if (courses.length) {
      const haystack = [...(item.courses ?? []), ...(item.focusAreas ?? [])];
      if (!courses.some((course) => haystack.includes(course))) return false;
    }

    const status = filters.status ?? [];
    if (status.length && status.includes("Closed") && !status.includes("Ongoing")) {
      return false;
    }

    return true;
  });
}

export function deadlineToIso(label?: string) {
  if (!label) return null;
  const cleaned = label.replace(/(\d+)(st|nd|rd|th)/, "$1");
  const date = new Date(cleaned);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString().slice(0, 10);
}
