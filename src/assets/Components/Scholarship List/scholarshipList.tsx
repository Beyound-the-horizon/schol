import "./scholarshipList.css";
import type { Scholarship } from "../../../data/scholarships";
import RowItem from "../Row item/rowItem";

type ScholarshipListProps = {
  scholarships: Scholarship[];
};

export default function ScholarshipList({
  scholarships,
}: ScholarshipListProps) {
  return (
    <div className="scholarshipList">
        {scholarships.map((scholarship) => (
          <RowItem
            key={scholarship.id}
            name={scholarship.name}
            location={scholarship.location}
            organization={scholarship.organization}
            offer={scholarship.offer}
            eligibility={scholarship.eligibility}
            deadline={scholarship.deadline}
          />
        ))}
    </div>
  );
}
