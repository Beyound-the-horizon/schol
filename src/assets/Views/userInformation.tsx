import { Eye, Plus, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { toast } from "sonner";
import IconItem from "../Components/Icon item/iconItem";
import FieldItem from "../Components/Field item/fieldItem";
import ButtonItem from "../Components/Button item/buttonItem";
import DocumentPreview from "../Components/Document preview/documentPreview";
import { nationalities, courseStudiedOptions } from "../../data/scholarships";
import {
  connectGoogleAccount,
  disconnectGoogleAccount,
  loadStoredAccount,
  syncCalendarEvents,
  type GoogleAccount,
} from "../../lib/googleAccount";
import "./userInformation.css";

type UserInformationProps = {
  onClose: () => void;
  calendarEvents?: { title: string; date: string }[];
};

type SlotFile = {
  file: File;
  url: string;
  name: string;
  kind: "image" | "pdf" | "file";
};

const SLOTS = [
  { id: "cv", label: "CV" },
  { id: "transcript", label: "Transcript" },
  { id: "id", label: "ID" },
  { id: "photo", label: "Photograph" },
  { id: "english", label: "English proficiency" },
  { id: "rec1", label: "1\nRecommendation" },
  { id: "rec2", label: "2\nRecommendation" },
  { id: "rec3", label: "3\nRecommendation" },
];

const SCALES = ["4.0", "5.0", "7.0", "10", "100"];

function labelForSlot(id: string) {
  return SLOTS.find((slot) => slot.id === id)?.label.replace("\n", " ") ?? "Document";
}

function fileKind(file: File): SlotFile["kind"] {
  if (file.type.startsWith("image/")) return "image";
  if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
    return "pdf";
  }
  return "file";
}

export default function UserInformation({
  onClose,
  calendarEvents = [],
}: UserInformationProps) {
  const [files, setFiles] = useState<Record<string, SlotFile | null>>({});
  const [viewer, setViewer] = useState<SlotFile | null>(null);
  const [pendingSlot, setPendingSlot] = useState<string | null>(null);
  const [scale, setScale] = useState("5.0");
  const [account, setAccount] = useState<GoogleAccount | null>(() =>
    loadStoredAccount()
  );
  const [connecting, setConnecting] = useState(false);
  const [nationality, setNationality] = useState("");
  const [courseStudied, setCourseStudied] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const filesRef = useRef(files);
  filesRef.current = files;

  useEffect(() => {
    if (!viewer) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setViewer(null);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [viewer]);

  useEffect(() => {
    return () => {
      Object.values(filesRef.current).forEach((file) => {
        if (file) URL.revokeObjectURL(file.url);
      });
    };
  }, []);

  function openPicker(id: string) {
    setPendingSlot(id);
    fileInputRef.current?.click();
  }

  function onFileChosen(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    const slotId = pendingSlot;
    event.target.value = "";
    setPendingSlot(null);
    if (!file || !slotId) return;

    const url = URL.createObjectURL(file);
    setFiles((current) => {
      const previous = current[slotId];
      if (previous) URL.revokeObjectURL(previous.url);
      return {
        ...current,
        [slotId]: { file, url, name: file.name, kind: fileKind(file) },
      };
    });
    toast(`${labelForSlot(slotId)} updated`, { id: `doc-${slotId}` });
  }

  function removeFile(id: string) {
    setFiles((current) => {
      const previous = current[id];
      if (previous) URL.revokeObjectURL(previous.url);
      return { ...current, [id]: null };
    });
    setViewer((current) => (current && files[id]?.url === current.url ? null : current));
    toast(`${labelForSlot(id)} removed`, { id: `doc-${id}-removed` });
  }

  async function onConnect() {
    setConnecting(true);
    try {
      const next = await connectGoogleAccount();
      setAccount(next);
      toast(`Connected ${next.email}`);
      if (Notification.permission === "default") {
        await Notification.requestPermission();
      }
      const dated = calendarEvents.filter((event) => event.date);
      if (dated.length) {
        await syncCalendarEvents(next, dated);
        toast("Calendar synced");
      }
    } catch (error) {
      toast(error instanceof Error ? error.message : "Could not connect Gmail");
    } finally {
      setConnecting(false);
    }
  }

  async function onDisconnect() {
    await disconnectGoogleAccount(account);
    setAccount(null);
    toast("Gmail disconnected");
  }

  const nationalitySuggestion = nationalities.find((item) =>
    item.toLowerCase().startsWith(nationality.trim().toLowerCase())
  );

  const courseStudiedSuggestion = courseStudiedOptions.find((item) =>
    item.toLowerCase().startsWith(courseStudied.trim().toLowerCase())
  );

  return (
    <div className="userInformation">
      <input
        ref={fileInputRef}
        className="hiddenFileInput"
        type="file"
        tabIndex={-1}
        accept="image/*,.pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        onChange={onFileChosen}
      />

      <div className="panel">
        <header className="panelHeader">
          <p>User Information</p>
          <IconItem
            size={32}
            icon={<X size={14} strokeWidth={1.5} />}
            aria-label="Close user information"
            onClick={onClose}
          />
        </header>

        <section className="infoSection">
          <h2>Personal</h2>
          <div className="fieldGroup">
            <span className="fieldLabel">Name</span>
            <div className="nameRow">
              <FieldItem placeholder="First" autoComplete="given-name" name="given-name" />
              <FieldItem placeholder="Middle" autoComplete="additional-name" name="additional-name" />
              <FieldItem placeholder="Last" autoComplete="family-name" name="family-name" />
            </div>
          </div>
          <div className="splitRow">
            <div className="fieldGroup narrow">
              <span className="fieldLabel">Nationality</span>
              <div className="nationalitySearch">
                {nationality && nationalitySuggestion ? (
                  <span className="locationGhost" aria-hidden="true">
                    <span className="locationGhostTyped">{nationality}</span>
                    <span className="locationGhostRest">
                      {nationalitySuggestion.slice(nationality.length)}
                    </span>
                  </span>
                ) : null}
                <FieldItem
                  placeholder="Nigerian, American..."
                  autoComplete="off"
                  value={nationality}
                  aria-label="Nationality"
                  aria-autocomplete="list"
                  onChange={(event) => setNationality(event.target.value)}
                  onKeyDown={(event) => {
                    if (
                      (event.key === "Tab" || event.key === "Enter") &&
                      nationality &&
                      nationalitySuggestion
                    ) {
                      event.preventDefault();
                      setNationality(nationalitySuggestion);
                    }
                  }}
                />
              </div>
            </div>
            <div className="fieldGroup wide">
              <span className="fieldLabel">Gmail</span>
              {account ? (
                <div className="gmailConnected">
                  <span>{account.email}</span>
                  <ButtonItem size={24} text="Disconnect" onClick={() => void onDisconnect()} />
                </div>
              ) : (
                <ButtonItem
                  className="gmailConnectButton"
                  size={32}
                  text={connecting ? "Connecting..." : "Connect Gmail"}
                  onClick={() => void onConnect()}
                />
              )}
            </div>
          </div>
        </section>

        <section className="infoSection">
          <h2>Academic</h2>
          <div className="splitRow">
            <div className="fieldGroup narrow">
              <span className="fieldLabel">Cgpa</span>
              <div className="cgpaRow">
                <FieldItem placeholder="3.80" inputMode="decimal" />
                <div className="scalePicker" role="group" aria-label="CGPA scale">
                  {SCALES.map((value) => (
                    <ButtonItem
                      key={value}
                      size={24}
                      text={value}
                      state={scale === value ? "active" : "default"}
                      onClick={() => setScale(value)}
                    />
                  ))}
                </div>
              </div>
            </div>
            <div className="fieldGroup wide">
              <span className="fieldLabel">Course studied</span>
              <div className="courseStudiedSearch">
                {courseStudied && courseStudiedSuggestion ? (
                  <span className="locationGhost" aria-hidden="true">
                    <span className="locationGhostTyped">{courseStudied}</span>
                    <span className="locationGhostRest">
                      {courseStudiedSuggestion.slice(courseStudied.length)}
                    </span>
                  </span>
                ) : null}
                <FieldItem
                  placeholder="B.eng Mechatronics Engineering"
                  autoComplete="off"
                  list="course-studied-options"
                  value={courseStudied}
                  aria-label="Course studied"
                  aria-autocomplete="list"
                  onChange={(event) => setCourseStudied(event.target.value)}
                  onKeyDown={(event) => {
                    if (
                      (event.key === "Tab" || event.key === "Enter") &&
                      courseStudied &&
                      courseStudiedSuggestion
                    ) {
                      event.preventDefault();
                      setCourseStudied(courseStudiedSuggestion);
                    }
                  }}
                />
                <datalist id="course-studied-options">
                  {courseStudiedOptions.map((opt) => (
                    <option key={opt} value={opt} />
                  ))}
                </datalist>
              </div>
            </div>
          </div>
        </section>

        <section className="infoSection">
          <h2>Documents</h2>
          <p className="documentHint">
            Upload PDF, Word, or image. We keep the original and preview page one, then
            export in whatever format a scholarship asks for.
          </p>
          <div className="documentGrid">
            {SLOTS.map((slot) => {
              const file = files[slot.id];
              const label = slot.label.replace("\n", " ");
              return (
                <div key={slot.id} className="documentSlot">
                  {file ? (
                    <div className="documentCard filled">
                      <DocumentPreview
                        file={file.file}
                        url={file.url}
                        kind={file.kind}
                        alt={file.name}
                      />
                      <span className="documentOverlay">
                        <IconItem
                          size={24}
                          aria-label={`View ${label}`}
                          icon={<Eye size={14} strokeWidth={1.5} />}
                          onClick={() => setViewer(file)}
                        />
                        <IconItem
                          size={24}
                          aria-label={`Remove ${label}`}
                          icon={<Trash2 size={14} strokeWidth={1.5} />}
                          onClick={() => removeFile(slot.id)}
                        />
                      </span>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="documentCard empty"
                      aria-label={`Add ${label}`}
                      onClick={() => openPicker(slot.id)}
                    >
                      <Plus size={14} strokeWidth={1.5} />
                    </button>
                  )}
                  <p>{slot.label}</p>
                </div>
              );
            })}
          </div>
        </section>
      </div>

      {viewer ? (
        <div
          className="documentViewer"
          role="dialog"
          aria-modal="true"
          aria-label={viewer.name}
        >
          <button
            type="button"
            className="documentViewerBackdrop"
            aria-label="Close document"
            onClick={() => setViewer(null)}
          />
          {viewer.kind === "image" ? (
            <img src={viewer.url} alt={viewer.name} />
          ) : (
            <iframe title={viewer.name} src={viewer.url} />
          )}
          <IconItem
            className="documentViewerClose"
            size={32}
            aria-label="Close document"
            icon={<X size={14} strokeWidth={1.5} />}
            onClick={() => setViewer(null)}
          />
        </div>
      ) : null}
    </div>
  );
}
