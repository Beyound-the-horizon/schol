import "./shortcutBar.css";

export type ShortcutHint = {
  label: string;
  keys: string[];
};

type ShortcutBarProps = {
  hints: ShortcutHint[];
  placement?: "overlay" | "embedded";
};

export default function ShortcutBar({
  hints,
  placement = "embedded",
}: ShortcutBarProps) {
  if (hints.length === 0) return null;

  return (
    <div
      className="shortcutBar"
      data-placement={placement}
      role="status"
      aria-label="Keyboard shortcuts"
    >
      <div className="shortcutGroup">
        {hints.map((hint, index) => (
          <span key={`${hint.label}-${index}`} className="shortcutHint">
            {index > 0 ? <span className="shortcutRule" /> : null}
            <span>{hint.label}</span>
            {hint.keys.map((key) => (
              <kbd key={key}>{key}</kbd>
            ))}
          </span>
        ))}
      </div>
    </div>
  );
}
