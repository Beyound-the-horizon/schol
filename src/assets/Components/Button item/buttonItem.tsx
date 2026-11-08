import "./buttonitem.css";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type buttonItemProps = {
  text?: string;
  showText?: boolean;
  LeftIcon?: ReactNode;
  RightIcon?: ReactNode;
  size?: 24 | 28 | 32 | 40 | 44;
  state?: "default" | "active";
  filled?: boolean;
  interactive?: boolean;
} & ButtonHTMLAttributes<HTMLButtonElement>;

export default function buttonitem({
  text,
  showText = true,
  size = 32,
  LeftIcon,
  RightIcon,
  state = "default",
  filled = false,
  interactive = true,
  type = "button",
  className,
  ...props
}: buttonItemProps) {
  const classes = ["buttonItem", className].filter(Boolean).join(" ");

  if (!interactive) {
    return (
      <span
        className={classes}
        data-size={size}
        data-state={state}
        data-filled={filled}
        data-static="true"
      >
        <span className="dataitem">
          {LeftIcon && <span className="leftIcon">{LeftIcon}</span>}
          {showText && text ? <span className="text">{text}</span> : null}
          {RightIcon && <span className="rightIcon">{RightIcon}</span>}
        </span>
      </span>
    );
  }

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
        {LeftIcon && <span className="leftIcon">{LeftIcon}</span>}
        {showText && text ? <span className="text">{text}</span> : null}
        {RightIcon && <span className="rightIcon">{RightIcon}</span>}
      </span>
    </button>
  );
}
