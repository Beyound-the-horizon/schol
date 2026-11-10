import "./fieldItem.css";
import type { InputHTMLAttributes } from "react";

type FieldItemProps = InputHTMLAttributes<HTMLInputElement> & {
  size?: 24 | 28 | 32;
  tone?: "placeholder" | "value";
};

export default function fielditem({
  size = 32,
  tone,
  className,
  ...props
}: FieldItemProps) {
  const classes = ["fieldItem", className].filter(Boolean).join(" ");

  return (
    <input
      className={classes}
      data-size={size}
      data-tone={tone}
      {...props}
    />
  );
}
