import "./rowItem.css";

type RowItemProps = {
  name: string;
  location: string;
  organization: string;
  offer: string;
  eligibility: string;
  deadline: string;
  size?: 48;
  state?: "default" | "active";
  filled?: boolean;
};

export default function RowItem({
  name,
  location,
  organization,
  offer,
  eligibility,
  deadline,
  size = 48,
  state = "default",
  filled = false,
}: RowItemProps) {
  return (
    <button
      className="rowItem"
      data-size={size}
      data-state={state}
      data-filled={filled}
    >
      <div className="mainContent">
        <span className="scholarshipname">{name}</span>
        <span className="scholarshiplocation">{location}</span>
      </div>

      <div className="infoContent">
        <span className="organization">{organization}</span>
        <span className="offer">{offer}</span>
        <span className="eligibility">{eligibility}</span>
        <span className="deadline">{deadline}</span>
      </div>
    </button>
  );
}
