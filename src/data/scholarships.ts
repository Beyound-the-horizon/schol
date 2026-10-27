export type Scholarship = {
    id: number;
    name: string;
    location: string;
    organization: string;
    offer: string;
    eligibility: string;
    deadline: string;
  };
  
  const base: Omit<Scholarship, "id">[] = [
    {
      name: "University of Michigan Scholarships",
      location: "Michigan, United States",
      organization: "Institution",
      offer: "Fully-funded",
      eligibility: "Eligible",
      deadline: "20th March 3mo",
    },
    {
      name: "Chevening Scholarships",
      location: "United Kingdom",
      organization: "Government",
      offer: "Fully-funded",
      eligibility: "Eligible",
      deadline: "5th November 1mo",
    },
    {
      name: "DAAD Helmut-Schmidt Programme",
      location: "Germany",
      organization: "Foundation",
      offer: "Partial",
      eligibility: "Not eligible",
      deadline: "31st August 10mo",
    },
    {
      name: "Mastercard Foundation Scholars Programme",
      location: "Multiple countries",
      organization: "Foundation",
      offer: "Fully-funded",
      eligibility: "Eligible",
      deadline: "12th January 2mo",
    },
  ];
  
  export const scholarships: Scholarship[] = Array.from(
    { length: 16 },
    (_, i) => ({ ...base[i % base.length], id: i + 1 })
);



