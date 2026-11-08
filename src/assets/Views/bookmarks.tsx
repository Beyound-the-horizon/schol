import { Trash2, X } from "lucide-react";
import IconItem from "../Components/Icon item/iconItem";
import type { Scholarship } from "../../data/scholarships";
import "./bookmarks.css";

type BookmarksProps = {
  scholarships: Scholarship[];
  onClose: () => void;
  onOpenScholarship: (id: number) => void;
  onRemove: (id: number) => void;
};

export default function Bookmarks({
  scholarships,
  onClose,
  onOpenScholarship,
  onRemove,
}: BookmarksProps) {
  return (
    <div className="bookmarks">
      <header className="bookmarksHeader">
        <div className="bookmarksHeaderInner">
          <p>Bookmarks</p>
          <IconItem
            size={32}
            icon={<X size={14} strokeWidth={1.5} />}
            aria-label="Close bookmarks"
            onClick={onClose}
          />
        </div>
      </header>

      <div className="bookmarkList">
        {scholarships.length === 0 ? (
          <p className="bookmarkEmpty">No bookmarks yet</p>
        ) : (
          scholarships.map((scholarship) => (
            <div key={scholarship.id} className="bookmarkRow">
              <button
                type="button"
                className="bookmarkName"
                onClick={() => onOpenScholarship(scholarship.id)}
              >
                {scholarship.name}
              </button>
              <IconItem
                size={24}
                icon={<Trash2 size={14} strokeWidth={1.5} />}
                aria-label={`Remove ${scholarship.name}`}
                onClick={() => onRemove(scholarship.id)}
              />
            </div>
          ))
        )}
      </div>
    </div>
  );
}
