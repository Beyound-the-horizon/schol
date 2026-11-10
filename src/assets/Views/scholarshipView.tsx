import { useMemo, useState, type ReactNode } from "react";
import { Bookmark, ExternalLink, Info, X } from "lucide-react";
import ButtonItem from "../Components/Button item/buttonItem";
import IconItem from "../Components/Icon item/iconItem";
import FieldItem from "../Components/Field item/fieldItem";
import TopBar from "../Components/Top bar/topBar";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import type { Filters } from "../Components/Search bar/searchbarItem";
import { getCourseDetails, type Scholarship } from "../../data/scholarships";
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
  label: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="detailRow">
      <div className="detailLabel">{label}</div>
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

            <div className="detailBlock">
              <DetailRow label="Letter of recommendation">
                {scholarship.recommendations}
              </DetailRow>
              <DetailRow label="English proficiency">
                {scholarship.english}
              </DetailRow>
              <DetailRow
                label={
                  <span className="documentsLabelWithInfo">
                    <span>Documents</span>
                    <HoverCard openDelay={100} closeDelay={150}>
                      <HoverCardTrigger asChild>
                        <button
                          type="button"
                          className="infoIconButton"
                          aria-label="Document format requirements"
                        >
                          <Info size={13} strokeWidth={1.5} />
                        </button>
                      </HoverCardTrigger>
                      <HoverCardContent side="right" align="start" className="documentsHoverCard">
                        <div className="hoverCardTitle">Accepted Formats</div>
                        <div className="hoverCardContentList">
                          {(scholarship.documentRequirements ?? [
                            { name: "CV", formats: ["PDF"], maxSize: "5 MB" },
                            { name: "Transcript", formats: ["PDF", "JPG"], maxSize: "10 MB" },
                            { name: "Passport", formats: ["PDF", "PNG", "JPG"], maxSize: "5 MB" },
                            { name: "Photograph", formats: ["JPG", "PNG"], maxSize: "500 KB" },
                          ]).map((requirement) => (
                            <div key={requirement.name} className="hoverCardRow">
                              <span className="hoverCardDoc">{requirement.name}</span>
                              <div className="hoverCardBadgeGroup">
                                {requirement.formats.map((format) => (
                                  <span key={format} className="hoverCardFormatBadge">
                                    {format}
                                  </span>
                                ))}
                                {requirement.maxSize ? (
                                  <span className="hoverCardMaxSize">
                                    ({requirement.maxSize})
                                  </span>
                                ) : null}
                              </div>
                            </div>
                          ))}
                        </div>
                      </HoverCardContent>
                    </HoverCard>
                  </span>
                }
              >
                <div className="documentNamesList">
                  {(scholarship.documentRequirements ?? []).length > 0
                    ? scholarship.documentRequirements?.map((requirement) => (
                        <span key={requirement.name} className="documentNameItem">
                          {requirement.name}
                        </span>
                      ))
                    : scholarship.documents}
                </div>
              </DetailRow>
              <DetailRow label="Motivation letter">
                {scholarship.motivation}
              </DetailRow>
            </div>

            <div className="detailBlock last">
              <DetailRow label="Visa and scholarship limitations">
                <div className="limitationStack">
                  <span className="limitationTitle">
                    {scholarship.returnToHomeCountry
                      ? "Return to home country required"
                      : "No return requirement"}
                  </span>
                  <p className="limitationNote">
                    {scholarship.returnToHomeCountryNote ??
                      (scholarship.returnToHomeCountry
                        ? "Scholars are obligated under scholarship and visa conditions to return to their home country for a mandatory period upon program completion."
                        : "Scholars have no mandatory home country return condition and are eligible to apply for post-study work permits or stay in the host country.")}
                  </p>
                </div>
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
                <Accordion type="single" collapsible className="courseAccordion">
                  {visibleCourses.map((course, index) => {
                    const details = getCourseDetails(course);
                    return (
                      <AccordionItem key={`${course}-${index}`} value={`course-${index}`}>
                        <AccordionTrigger className="courseAccordionTrigger">
                          <span className="courseTriggerText">{course}</span>
                        </AccordionTrigger>
                        <AccordionContent className="courseAccordionContent">
                          <div className="courseDetailsBody">
                            <p className="courseParagraph">
                              {details.description}
                            </p>
                            <p className="courseParagraph">
                              <strong>Duration:</strong> {details.duration}
                            </p>
                            <p className="courseParagraph">
                              <strong>Language taught in:</strong> {details.language}
                            </p>
                            <p className="courseParagraph courseUrlParagraph">
                              <a
                                href={details.courseUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="courseUrlLink"
                              >
                                View course curriculum
                                <ExternalLink size={12} strokeWidth={1.5} />
                              </a>
                            </p>
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                    );
                  })}
                </Accordion>
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
                <Accordion type="single" collapsible className="courseAccordion">
                  {focusAreas.map((area, index) => {
                    const details = getCourseDetails(area);
                    return (
                      <AccordionItem key={`${area}-${index}`} value={`area-${index}`}>
                        <AccordionTrigger className="courseAccordionTrigger">
                          <span className="courseTriggerText">{area}</span>
                        </AccordionTrigger>
                        <AccordionContent className="courseAccordionContent">
                          <div className="courseDetailsBody">
                            <p className="courseParagraph">
                              {details.description}
                            </p>
                            <p className="courseParagraph">
                              <strong>Duration:</strong> {details.duration}
                            </p>
                            <p className="courseParagraph">
                              <strong>Language taught in:</strong> {details.language}
                            </p>
                            <p className="courseParagraph courseUrlParagraph">
                              <a
                                href={details.courseUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="courseUrlLink"
                              >
                                Explore course opportunities
                                <ExternalLink size={12} strokeWidth={1.5} />
                              </a>
                            </p>
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                    );
                  })}
                </Accordion>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
