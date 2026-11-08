import { useMemo, useState, type ReactNode } from "react";
import { Bookmark, ChevronDown, ExternalLink, X } from "lucide-react";
import ButtonItem from "../Components/Button item/buttonItem";
import IconItem from "../Components/Icon item/iconItem";
import FieldItem from "../Components/Field item/fieldItem";
import TopBar from "../Components/Top bar/topBar";
import type { Filters } from "../Components/Search bar/searchbarItem";
import type { Scholarship } from "../../data/scholarships";
import "./scholarshipView.css";

type ScholarshipViewProps = {
  scholarship: Scholarship;
  scholarships: Scholarship[];
  bookmarked: boolean;
  source: "home" | "bookmarks";
  onBack: () => void;
  onOpenSearch: () => void;
  onOpenProfile: () => void;
  onOpenBookmarks: () => void;
  onToggleBookmark: () => void;
  searchOpen: boolean;
  onCloseSearch: () => void;
  onSelectScholarship: (id: number) => void;
  filters?: Filters;
  onFiltersChange?: (filters: Filters) => void;
  onClearFilters?: () => void;
};

function DetailRow({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="detailRow">
      <span className="detailLabel">{label}</span>
      <div className="detailValue">{children}</div>
    </div>
  );
}

export default function ScholarshipView({
  scholarship,
  scholarships,
  bookmarked,
  source,
  onBack,
  onOpenSearch,
  onOpenProfile,
  onOpenBookmarks,
  onToggleBookmark,
  searchOpen,
  onCloseSearch,
  onSelectScholarship,
  filters,
  onFiltersChange,
  onClearFilters,
}: ScholarshipViewProps) {
  const isInstitutional = scholarship.organization === "Institution";
  const courses = scholarship.courses ?? [];
  const focusAreas = scholarship.focusAreas ?? [];
  const [courseQuery, setCourseQuery] = useState("");
  const visibleCourses = useMemo(
    () =>
      courses.filter((course) =>
        course.toLowerCase().includes(courseQuery.trim().toLowerCase())
      ),
    [courses, courseQuery]
  );

  return (
    <div className="scholarshipView">
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

      <section className="scholarshipContent">
        <nav className="breadcrumb">
          <ButtonItem size={28} text="Home" onClick={onBack} />
          {source === "bookmarks" ? (
            <>
              <span className="crumbDivider">/</span>
              <ButtonItem size={28} text="Bookmark" onClick={onOpenBookmarks} />
            </>
          ) : null}
        </nav>

        <div className="scholarshipHeader">
          <h1>{scholarship.name}</h1>
          <div className="scholarshipActions">
            <ButtonItem
              size={32}
              filled
              text="Apply"
              LeftIcon={<ExternalLink size={14} strokeWidth={2} />}
            />
            <IconItem
              size={32}
              filled
              icon={<Bookmark size={14} strokeWidth={2} fill={bookmarked ? "currentColor" : "none"} />}
              aria-label="Bookmark scholarship"
              onClick={onToggleBookmark}
            />
          </div>
        </div>

        <div className="scholarshipBody">
          <div className="detailColumn">
            <div className="detailBlock">
              <DetailRow label="Source">{scholarship.source ?? "Url"}</DetailRow>
              <DetailRow label="Location">{scholarship.location}</DetailRow>
              <DetailRow label="Application deadline">
                <span className="deadlinePrimary">{scholarship.deadlineDate}</span>
                <span className="deadlineSecondary">{scholarship.daysLeft}</span>
              </DetailRow>
              <DetailRow label="Eligibility">
                {scholarship.eligibilityDetail}
              </DetailRow>
              <DetailRow label="Type">{scholarship.organization}</DetailRow>
              <DetailRow label="Funding">
                <div className="fundingStack">
                  <span>{scholarship.offer}</span>
                  {(scholarship.benefits ?? ["Travel", "Living", "Stipend"]).map(
                    (benefit) =>
                      benefit === "Stipend" ? (
                        <div key={benefit} className="stipendRow">
                          <ButtonItem
                            size={24}
                            interactive={false}
                            text="Stipend"
                            LeftIcon={<X size={14} strokeWidth={2} />}
                          />
                          <span className="stipendAmount">{scholarship.stipend}</span>
                        </div>
                      ) : (
                        <ButtonItem
                          key={benefit}
                          size={24}
                          interactive={false}
                          text={benefit}
                          LeftIcon={<X size={14} strokeWidth={2} />}
                        />
                      )
                  )}
                </div>
              </DetailRow>
              <DetailRow label="Duration">{scholarship.duration}</DetailRow>
            </div>

            <div className="detailBlock">
              <DetailRow label="Minimum CGPA">{scholarship.minCgpa}</DetailRow>
              <DetailRow label="Work experience">
                {scholarship.workExperience}
              </DetailRow>
            </div>

            <div className="detailBlock last">
              <DetailRow label="Letter of recommendation">
                {scholarship.recommendations}
              </DetailRow>
              <DetailRow label="English proficiency">
                {scholarship.english}
              </DetailRow>
              <DetailRow label="Documents">
                <div className="formatList">
                  {(scholarship.documentRequirements ?? []).length > 0
                    ? scholarship.documentRequirements?.map((requirement) => (
                        <span key={requirement.name} className="formatRow">
                          {requirement.name}
                          <span className="formatTags">
                            {requirement.formats.map((format) => (
                              <ButtonItem
                                key={format}
                                size={24}
                                interactive={false}
                                text={format}
                              />
                            ))}
                          </span>
                        </span>
                      ))
                    : scholarship.documents}
                </div>
              </DetailRow>
              <DetailRow label="Motivation letter">
                {scholarship.motivation}
              </DetailRow>
            </div>
          </div>

          {isInstitutional ? (
            <div className="courseColumn">
              <FieldItem
                placeholder="Search courses"
                value={courseQuery}
                onChange={(event) => setCourseQuery(event.target.value)}
              />
              <div className="courseList">
                {visibleCourses.map((course, index) => (
                  <div key={`${course}-${index}`} className="courseRow">
                    <span>{course}</span>
                    <ChevronDown size={14} strokeWidth={2} />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="courseColumn coverageColumn">
              <div>
                <p className="coverageKicker">{scholarship.organization}</p>
                <h2>Coverage</h2>
                <p className="coverageCopy">
                  {scholarship.selection ??
                    "This award is not tied to one university course list. Match on field, then pick a host later."}
                </p>
              </div>
              <div className="courseList">
                {focusAreas.map((area) => (
                  <div key={area} className="courseRow">
                    <span>{area}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
