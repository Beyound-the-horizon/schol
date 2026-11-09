export type ScholarshipKind =
  | "Institution"
  | "Organization"
  | "Foundation"
  | "Government";

export type DocumentRequirement = {
  name: string;
  formats: string[];
  maxSize: string;
};

export type CourseDetail = {
  name: string;
  department: string;
  duration: string;
  language: string;
  notes: string;
};

export type Scholarship = {
  id: number;
  name: string;
  location: string;
  organization: ScholarshipKind;
  offer: string;
  eligibility: string;
  deadline: string;
  source?: string;
  deadlineDate?: string;
  daysLeft?: string;
  eligibilityDetail?: string;
  duration?: string;
  minCgpa?: string;
  workExperience?: string;
  recommendations?: string;
  english?: string;
  documents?: string;
  motivation?: string;
  stipend?: string;
  courses?: string[];
  focusAreas?: string[];
  benefits?: string[];
  documentRequirements?: DocumentRequirement[];
  selection?: string;
  official_url?: string;
};

const base: Omit<Scholarship, "id">[] = [
  {
    name: "University of Michigan Scholarships",
    location: "Michigan, United States",
    organization: "Institution",
    offer: "Fully-funded",
    eligibility: "Eligible",
    deadline: "20th March 3mo",
    source: "Url",
    deadlineDate: "20th March, 2027",
    daysLeft: "90 days",
    eligibilityDetail: "Available to Nigerians",
    duration: "1.5 Years",
    minCgpa: "4.5",
    workExperience: "Required",
    recommendations: "3",
    english: "TOEFL/IELTS",
    documents: "CV, transcript, international passport, photograph",
    motivation: "Whatever it requires",
    stipend: "$1,100/mo",
    courses: Array.from({ length: 14 }, () => "Msc Mechatronics Engineering"),
    benefits: ["Travel", "Living", "Stipend"],
    documentRequirements: [
      { name: "CV", formats: ["PDF"], maxSize: "5 MB" },
      { name: "Transcript", formats: ["PDF", "JPG"], maxSize: "10 MB" },
      { name: "Passport", formats: ["PDF", "PNG", "JPG"], maxSize: "5 MB" },
      { name: "Photograph", formats: ["JPG", "PNG"], maxSize: "500 KB" },
    ],
  },
  {
    name: "Chevening Scholarships",
    location: "United Kingdom",
    organization: "Government",
    offer: "Fully-funded",
    eligibility: "Eligible",
    deadline: "5th November 1mo",
    source: "Url",
    deadlineDate: "5th November, 2026",
    daysLeft: "30 days",
    eligibilityDetail: "Available to Nigerians",
    duration: "1 Year",
    minCgpa: "4.0",
    workExperience: "Required",
    recommendations: "2",
    english: "IELTS",
    documents: "CV, transcript, passport",
    motivation: "Required",
    stipend: "£1,347/mo",
    courses: ["Msc Public Policy", "Msc International Relations"],
    focusAreas: ["Public policy", "International relations", "Climate", "Health"],
    benefits: ["Travel", "Living", "Stipend"],
    selection: "Essay, references, and interview. Any eligible UK master’s course.",
    documentRequirements: [
      { name: "CV", formats: ["PDF", "DOCX"], maxSize: "3 MB" },
      { name: "Transcript", formats: ["PDF"], maxSize: "8 MB" },
      { name: "Passport", formats: ["PDF"], maxSize: "5 MB" },
    ],
  },
  {
    name: "DAAD Helmut-Schmidt Programme",
    location: "Germany",
    organization: "Foundation",
    offer: "Partial",
    eligibility: "Not eligible",
    deadline: "31st August 10mo",
    source: "Url",
    deadlineDate: "31st August, 2027",
    daysLeft: "10 months",
    eligibilityDetail: "Not available",
    duration: "2 Years",
    minCgpa: "3.5",
    workExperience: "Preferred",
    recommendations: "2",
    english: "TOEFL/IELTS",
    documents: "CV, transcript",
    motivation: "Required",
    stipend: "€934/mo",
    courses: ["Msc Development Studies"],
    focusAreas: ["Public policy", "Development studies", "Governance"],
    benefits: ["Living", "Stipend"],
    selection: "Host university nomination. Course list is indicative, not binding.",
    documentRequirements: [
      { name: "CV", formats: ["PDF"], maxSize: "2 MB" },
      { name: "Transcript", formats: ["PDF", "DOCX"], maxSize: "5 MB" },
    ],
  },
  {
    name: "Mastercard Foundation Scholars Programme",
    location: "Multiple countries",
    organization: "Foundation",
    offer: "Fully-funded",
    eligibility: "Eligible",
    deadline: "12th January 2mo",
    source: "Url",
    deadlineDate: "12th January, 2027",
    daysLeft: "2 months",
    eligibilityDetail: "Available to Nigerians",
    duration: "2 Years",
    minCgpa: "3.7",
    workExperience: "Not required",
    recommendations: "2",
    english: "TOEFL/IELTS",
    documents: "CV, transcript, photograph",
    motivation: "Required",
    stipend: "$1,200/mo",
    courses: ["Msc Agriculture", "Msc Public Health"],
    focusAreas: ["Agriculture", "Public health", "Education", "Climate"],
    benefits: ["Travel", "Living", "Stipend"],
    selection: "Partner-university placement after a common application.",
    documentRequirements: [
      { name: "CV", formats: ["PDF"], maxSize: "5 MB" },
      { name: "Transcript", formats: ["PDF"], maxSize: "10 MB" },
      { name: "Photograph", formats: ["JPG"], maxSize: "500 KB" },
    ],
  },
  {
    name: "Gates Cambridge Scholarship",
    location: "United Kingdom",
    organization: "Organization",
    offer: "Fully-funded",
    eligibility: "Eligible",
    deadline: "3rd December 1mo",
    source: "Url",
    deadlineDate: "3rd December, 2026",
    daysLeft: "28 days",
    eligibilityDetail: "Available to Nigerians",
    duration: "1–4 Years",
    minCgpa: "3.8",
    workExperience: "Preferred",
    recommendations: "2",
    english: "IELTS",
    documents: "CV, transcript, research proposal",
    motivation: "Required",
    stipend: "£21,000/yr",
    focusAreas: ["Any Cambridge postgraduate course", "Research leadership"],
    benefits: ["Travel", "Living", "Stipend"],
    selection: "Department ranking, then Gates interview. Not a single-course award.",
    documentRequirements: [
      { name: "CV", formats: ["PDF"], maxSize: "2 MB" },
      { name: "Transcript", formats: ["PDF", "DOCX"], maxSize: "10 MB" },
      { name: "Research proposal", formats: ["PDF", "DOCX"], maxSize: "5 MB" },
    ],
  },
];

export const scholarships: Scholarship[] = Array.from(
  { length: 17 },
  (_, i) => ({ ...base[i % base.length], id: i + 1 })
);

export const courseOptions = Array.from(
  new Set(
    scholarships.flatMap((item) => [
      ...(item.courses ?? []),
      ...(item.focusAreas ?? []),
    ])
  )
);

export const courseCatalog: Record<string, CourseDetail> = {
  "Msc Mechatronics Engineering": {
    name: "Msc Mechatronics Engineering",
    department: "Engineering",
    duration: "18 months",
    language: "English",
    notes: "Thesis track covering control systems, robotics and embedded design.",
  },
  "Msc Public Policy": {
    name: "Msc Public Policy",
    department: "Social sciences",
    duration: "12 months",
    language: "English",
    notes: "Policy analysis, economics and a dissertation with a UK host.",
  },
  "Msc International Relations": {
    name: "Msc International Relations",
    department: "Social sciences",
    duration: "12 months",
    language: "English",
    notes: "Diplomacy, security studies and a research methods core.",
  },
  "Msc Development Studies": {
    name: "Msc Development Studies",
    department: "Development",
    duration: "24 months",
    language: "English or German",
    notes: "Practice-oriented programme with a host-university placement.",
  },
  "Msc Agriculture": {
    name: "Msc Agriculture",
    department: "Agriculture",
    duration: "24 months",
    language: "English",
    notes: "Crop systems and food security with a partner university.",
  },
  "Msc Public Health": {
    name: "Msc Public Health",
    department: "Health",
    duration: "24 months",
    language: "English",
    notes: "Epidemiology, health systems and a field practicum.",
  },
};

export const nationalities = [
  "Nigerian",
  "American",
  "British",
  "Canadian",
  "Chinese",
  "Indian",
  "German",
  "Ghanaian",
  "Kenyan",
  "South African",
  "French",
  "Italian",
  "Spanish",
  "Japanese",
  "Algerian",
];
