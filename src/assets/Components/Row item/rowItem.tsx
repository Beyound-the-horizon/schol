import "./rowItem.css";
import type { ButtonHTMLAttributes } from "react";

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
} & ButtonHTMLAttributes<HTMLButtonElement>;

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
  type = "button",
  ...props
}: RowItemProps) {
  return (
    <button
      type={type}
      className="rowItem"
      data-size={size}
      data-state={state}
      data-filled={filled}
      {...props}
    >
      <div className="mainContent">
        <span className="scholarshipname" title={name}>{name}</span>
        <span className="scholarshiplocation" title={location}>{location}</span>
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
