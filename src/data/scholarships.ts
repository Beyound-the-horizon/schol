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
  department?: string;
  duration: string;
  language: string;
  description: string;
  courseUrl: string;
  notes?: string;
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
  returnToHomeCountry?: boolean;
  returnToHomeCountryNote?: string;
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
    courses: [
      "Msc Mechatronics Engineering",
      "Msc Robotics & Autonomous Systems",
      "Msc Computer Science & Engineering",
      "Msc Data Science",
      "Msc Biomedical Engineering",
      "Msc Mechanical Engineering",
      "Msc Electrical & Computer Engineering",
      "Msc Aerospace Engineering",
      "Msc Industrial & Operations Engineering",
      "Msc Civil & Environmental Engineering",
      "Msc Materials Science & Engineering",
      "Msc Climate & Space Sciences",
      "Msc Nuclear Engineering",
      "Msc Naval Architecture & Marine Engineering",
    ],
    benefits: ["Travel", "Living", "Stipend"],
    documentRequirements: [
      { name: "CV", formats: ["PDF"], maxSize: "5 MB" },
      { name: "Transcript", formats: ["PDF", "JPG"], maxSize: "10 MB" },
      { name: "Passport", formats: ["PDF", "PNG", "JPG"], maxSize: "5 MB" },
      { name: "Photograph", formats: ["JPG", "PNG"], maxSize: "500 KB" },
    ],
    returnToHomeCountry: false,
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
    returnToHomeCountry: true,
    returnToHomeCountryNote: "Scholars must return to their home country for at least two years after the scholarship ends. This is a strict visa condition tied to the Chevening award.",
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
    returnToHomeCountry: true,
    returnToHomeCountryNote: "DAAD scholars on this programme are expected to return to their home country after completing their studies to apply their knowledge to national development.",
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
    returnToHomeCountry: true,
    returnToHomeCountryNote: "Mastercard Foundation Scholars are expected to return to Africa and contribute to community development after completing their studies.",
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
    returnToHomeCountry: false,
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
    duration: "18 months (full-time)",
    language: "English",
    description: "An advanced interdisciplinary thesis program integrating mechanical engineering, electronics, computer science, and control systems. Students complete core laboratory modules in robotics design, embedded computing, and autonomous navigation.",
    courseUrl: "https://ece.engin.umich.edu/academics/graduate-programs/",
  },
  "Msc Robotics & Autonomous Systems": {
    name: "Msc Robotics & Autonomous Systems",
    department: "Robotics Institute",
    duration: "24 months (full-time)",
    language: "English",
    description: "Covers perception, control theory, machine learning, and bio-inspired robotics with hands-on research in world-class automated robotics laboratories.",
    courseUrl: "https://robotics.umich.edu/academic-programs/graduate/",
  },
  "Msc Computer Science & Engineering": {
    name: "Msc Computer Science & Engineering",
    department: "Computer Science",
    duration: "18 to 24 months (full-time)",
    language: "English",
    description: "Comprehensive graduate curriculum exploring distributed computing systems, artificial intelligence, cryptographic security, and human-computer interaction.",
    courseUrl: "https://cse.engin.umich.edu/academics/graduate/",
  },
  "Msc Data Science": {
    name: "Msc Data Science",
    department: "Information Science & Statistics",
    duration: "18 months (full-time)",
    language: "English",
    description: "Rigorous training in probabilistic modeling, big data infrastructure, statistical computation, and high-dimensional machine learning with enterprise capstone projects.",
    courseUrl: "https://midas.umich.edu/graduate-programs/",
  },
  "Msc Biomedical Engineering": {
    name: "Msc Biomedical Engineering",
    department: "Biomedical Engineering",
    duration: "20 months (full-time)",
    language: "English",
    description: "Translational research bridging computational neural engineering, medical imaging devices, and cellular tissue biomechanics.",
    courseUrl: "https://bme.umich.edu/academics/graduate/",
  },
  "Msc Mechanical Engineering": {
    name: "Msc Mechanical Engineering",
    department: "Mechanical Engineering",
    duration: "18 to 24 months (full-time)",
    language: "English",
    description: "Focuses on advanced thermal fluid dynamics, structural mechanics, advanced manufacturing, and sustainable energy conversion systems.",
    courseUrl: "https://me.engin.umich.edu/academics/graduate/",
  },
  "Msc Electrical & Computer Engineering": {
    name: "Msc Electrical & Computer Engineering",
    department: "Electrical Engineering",
    duration: "18 to 24 months (full-time)",
    language: "English",
    description: "Deep dive into solid-state electronics, integrated circuits, photonics, wireless communications, and power grid optimization.",
    courseUrl: "https://ece.engin.umich.edu/academics/graduate-programs/",
  },
  "Msc Aerospace Engineering": {
    name: "Msc Aerospace Engineering",
    department: "Aerospace Engineering",
    duration: "18 months (full-time)",
    language: "English",
    description: "Study of aerodynamics, propulsion dynamics, orbital flight mechanics, structural composites, and autonomous aerial guidance systems.",
    courseUrl: "https://aero.engin.umich.edu/academics/graduate/",
  },
  "Msc Industrial & Operations Engineering": {
    name: "Msc Industrial & Operations Engineering",
    department: "Industrial Engineering",
    duration: "18 months (full-time)",
    language: "English",
    description: "Mathematical optimization, stochastic modeling, supply chain logistics, operations research, and health systems engineering.",
    courseUrl: "https://ioe.engin.umich.edu/academics/graduate/",
  },
  "Msc Civil & Environmental Engineering": {
    name: "Msc Civil & Environmental Engineering",
    department: "Civil Engineering",
    duration: "18 to 24 months (full-time)",
    language: "English",
    description: "Smart infrastructure resilience, environmental biotechnology, structural health monitoring, and hydro-climatic sustainability.",
    courseUrl: "https://cee.engin.umich.edu/academics/graduate/",
  },
  "Msc Materials Science & Engineering": {
    name: "Msc Materials Science & Engineering",
    department: "Materials Science",
    duration: "24 months (full-time)",
    language: "English",
    description: "Nanotechnology, polymer science, quantum materials, and biomaterials characterization through advanced electron microscopy.",
    courseUrl: "https://mse.engin.umich.edu/academics/graduate/",
  },
  "Msc Climate & Space Sciences": {
    name: "Msc Climate & Space Sciences",
    department: "Climate & Space",
    duration: "24 months (full-time)",
    language: "English",
    description: "Atmospheric modeling, satellite remote sensing, space weather instrumentation, and planetary climate physics.",
    courseUrl: "https://clasp.engin.umich.edu/academics/graduate-programs/",
  },
  "Msc Nuclear Engineering": {
    name: "Msc Nuclear Engineering",
    department: "Nuclear Engineering & Radiological Sciences",
    duration: "24 months (full-time)",
    language: "English",
    description: "Nuclear fission reactors, plasma fusion containment, radiological imaging, and radiation detection instrumentation.",
    courseUrl: "https://ners.engin.umich.edu/academics/graduate/",
  },
  "Msc Naval Architecture & Marine Engineering": {
    name: "Msc Naval Architecture & Marine Engineering",
    department: "Marine Engineering",
    duration: "18 to 24 months (full-time)",
    language: "English",
    description: "Hydrodynamics, marine vessel structural acoustics, offshore wind energy structures, and autonomous marine robotics.",
    courseUrl: "https://name.engin.umich.edu/academics/graduate/",
  },
  "Msc Public Policy": {
    name: "Msc Public Policy",
    department: "Social sciences",
    duration: "12 months (full-time)",
    language: "English",
    description: "Intensive training in policy analysis, quantitative evaluation methods, public management, economics, and a mandatory dissertation completed with a partner UK institution.",
    courseUrl: "https://www.chevening.org/scholarships/find-a-course/",
  },
  "Msc International Relations": {
    name: "Msc International Relations",
    department: "Social sciences",
    duration: "12 months (full-time)",
    language: "English",
    description: "Explores contemporary multilateral diplomacy, international law, conflict negotiation, and strategic security architectures with renowned global affairs faculty.",
    courseUrl: "https://www.chevening.org/scholarships/find-a-course/",
  },
  "Msc Development Studies": {
    name: "Msc Development Studies",
    department: "Development Studies",
    duration: "24 months (full-time)",
    language: "English or German",
    description: "Practice-oriented curriculum addressing socioeconomic disparities, sustainable development goals, and international political economy with host university field placement in Germany.",
    courseUrl: "https://www.daad.de/en/study-and-research-in-germany/scholarships/",
  },
  "Msc Agriculture": {
    name: "Msc Agriculture",
    department: "Agriculture & Life Sciences",
    duration: "24 months (full-time)",
    language: "English",
    description: "Focuses on climate-resilient crop genetics, sustainable soil management, and food security value chains in partnership with leading global agricultural institutes.",
    courseUrl: "https://mastercardfdn.org/all/scholars/",
  },
  "Msc Public Health": {
    name: "Msc Public Health",
    department: "Health Sciences",
    duration: "24 months (full-time)",
    language: "English",
    description: "Comprehensive studies in epidemiology, infectious disease surveillance, biostatistics, and healthcare policy implementation with a mandatory field practicum.",
    courseUrl: "https://mastercardfdn.org/all/scholars/",
  },
};

export function getCourseDetails(courseName: string): CourseDetail {
  if (courseCatalog[courseName]) {
    return courseCatalog[courseName];
  }
  const cleanName = courseName.trim();
  return {
    name: cleanName,
    department: "Graduate Studies",
    duration: "12 to 24 months (full-time)",
    language: "English",
    description: `${cleanName} provides an in-depth curriculum focusing on foundational theory, advanced methodologies, and practical research applications tailored for postgraduate scholars.`,
    courseUrl: `https://www.google.com/search?q=${encodeURIComponent(cleanName + " master degree curriculum")}`,
  };
}

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

export const courseStudiedOptions = [
  "B.eng Mechatronics Engineering",
  "B.eng Mechanical Engineering",
  "B.eng Electrical Engineering",
  "B.eng Civil Engineering",
  "B.eng Computer Engineering",
  "B.sc Computer Science",
  "B.sc Mathematics",
  "B.sc Physics",
  "B.sc Chemistry",
  "B.sc Biology",
  "B.sc Economics",
  "B.sc Accounting",
  "B.sc Business Administration",
  "B.sc Statistics",
  "B.a English",
  "B.a History",
  "B.a Political Science",
  "B.a International Relations",
  "B.a Sociology",
  "B.a Psychology",
  "B.a Philosophy",
  "B.a Law",
  "B.sc Public Health",
  "B.sc Agriculture",
  "B.sc Environmental Science",
  "B.sc Biochemistry",
  "B.sc Microbiology",
  "B.sc Nursing",
  "B.pharm Pharmacy",
  "MBBS Medicine",
  "B.ed Education",
  "B.a Mass Communication",
  "B.sc Architecture",
  "B.a Fine Arts",
];
