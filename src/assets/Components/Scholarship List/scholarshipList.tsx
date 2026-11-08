import "./scholarshipList.css";
import type { Scholarship } from "../../../data/scholarships";
import RowItem from "../Row item/rowItem";

type ScholarshipListProps = {
  scholarships: Scholarship[];
  onSelect?: (id: number) => void;
};

export default function ScholarshipList({
  scholarships,
  onSelect,
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
          onClick={() => onSelect?.(scholarship.id)}
        />
      ))}
    </div>
  );
}
