import "./iconItem.css";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type IconItemProps = {
  icon?: ReactNode;
  size?: 24 | 28 | 32 | 40 | 44;
  state?: "default" | "active";
  filled?: boolean;
} & ButtonHTMLAttributes<HTMLButtonElement>;

export default function iconitem({
  icon,
  size = 32,
  state = "default",
  filled = false,
  type = "button",
  className,
  ...props
}: IconItemProps) {
  const classes = ["iconItem", className].filter(Boolean).join(" ");

  return (
    <button
      type={type}
      className={classes}
      data-size={size}
      data-state={state}
      data-filled={filled}
      {...props}
    >
      <span className="dataitem">
        {icon && <span className="icon">{icon}</span>}
      </span>
    </button>
  );
}
