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
import {
  fetchUserProfile,
  saveUserProfile,
  saveProfileDraft,
  uploadUserDocument,
  deleteUserDocument,
  getEffectiveUserId,
  type ProfileDocument,
  type UserProfile,
} from "../../services/profileService";
import "./userInformation.css";

type UserInformationProps = {
  onClose: () => void;
  calendarEvents?: { title: string; date: string }[];
};

type SlotFile = {
  file?: File | null;
  url: string;
  name: string;
  kind: "image" | "pdf" | "file";
  path?: string;
  size?: number;
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

export default function UserInformation({
  onClose,
  calendarEvents = [],
}: UserInformationProps) {
  const [firstName, setFirstName] = useState("");
  const [middleName, setMiddleName] = useState("");
  const [lastName, setLastName] = useState("");
  const [nationality, setNationality] = useState("");
  const [cgpa, setCgpa] = useState("");
  const [scale, setScale] = useState("5.0");
  const [courseStudied, setCourseStudied] = useState("");
  const [files, setFiles] = useState<Record<string, SlotFile | null>>({});
  const [viewer, setViewer] = useState<SlotFile | null>(null);
  const [pendingSlot, setPendingSlot] = useState<string | null>(null);
  const [account, setAccount] = useState<GoogleAccount | null>(() =>
    loadStoredAccount()
  );
  const [connecting, setConnecting] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const saveDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stateRef = useRef({
    firstName,
    middleName,
    lastName,
    nationality,
    cgpa,
    scale,
    courseStudied,
    files,
    account,
    isInitialLoading,
  });
  stateRef.current = {
    firstName,
    middleName,
    lastName,
    nationality,
    cgpa,
    scale,
    courseStudied,
    files,
    account,
    isInitialLoading,
  };

  // Load saved profile on mount
  useEffect(() => {
    let cancelled = false;

    async function init() {
      setIsInitialLoading(true);
      try {
        const uid = getEffectiveUserId();
        const profile = await fetchUserProfile(uid);
        if (cancelled) return;
        if (profile) {
          setFirstName(profile.firstName || "");
          setMiddleName(profile.middleName || "");
          setLastName(profile.lastName || "");
          setNationality(profile.nationality || "");
          setCgpa(profile.cgpa || "");
          if (profile.cgpaScale) setScale(profile.cgpaScale);
          setCourseStudied(profile.courseStudied || "");
          if (profile.documents) {
            const mappedFiles: Record<string, SlotFile | null> = {};
            for (const [k, doc] of Object.entries(profile.documents)) {
              if (doc && doc.url) {
                mappedFiles[k] = {
                  file: null,
                  url: doc.url,
                  name: doc.name || labelForSlot(k),
                  kind: doc.kind || "file",
                  path: doc.path,
                  size: doc.size,
                };
              }
            }
            setFiles(mappedFiles);
          }
        }
      } catch (err) {
        console.error("Failed to load user profile:", err);
      } finally {
        if (!cancelled) {
          setIsInitialLoading(false);
        }
      }
    }

    void init();
    return () => {
      cancelled = true;
    };
  }, []);

  // Save profile to Supabase (and localStorage draft fallback)
  async function persistProfile(showToast = true) {
    if (stateRef.current.isInitialLoading) return;
    const uid = getEffectiveUserId();
    const currentDocs: Record<string, ProfileDocument> = {};
    for (const [key, slot] of Object.entries(stateRef.current.files)) {
      if (slot && slot.url) {
        currentDocs[key] = {
          slotId: key,
          name: slot.name,
          url: slot.url,
          path: slot.path || "",
          kind: slot.kind,
          size: slot.size,
        };
      }
    }

    const profileData: UserProfile = {
      userId: uid,
      firstName: stateRef.current.firstName.trim(),
      middleName: stateRef.current.middleName.trim(),
      lastName: stateRef.current.lastName.trim(),
      nationality: stateRef.current.nationality.trim(),
      cgpa: stateRef.current.cgpa.trim(),
      cgpaScale: stateRef.current.scale,
      courseStudied: stateRef.current.courseStudied.trim(),
      gmail: stateRef.current.account?.email || "",
      documents: currentDocs,
    };

    saveProfileDraft(uid, profileData);

    try {
      if (showToast) {
        toast.loading("Saving...", { id: "save-indicator" });
      }
      await saveUserProfile(profileData);
      if (showToast) {
        toast.success("Saved", { id: "save-indicator", duration: 1500 });
      }
    } catch (err) {
      console.error("Save error:", err);
      toast.error(
        err instanceof Error ? err.message : "Failed to save profile (saved locally)",
        { id: "save-indicator" }
      );
    }
  }

  function triggerAutoSave() {
    if (isInitialLoading) return;
    const uid = getEffectiveUserId();
    saveProfileDraft(uid, {
      userId: uid,
      firstName: stateRef.current.firstName,
      middleName: stateRef.current.middleName,
      lastName: stateRef.current.lastName,
      nationality: stateRef.current.nationality,
      cgpa: stateRef.current.cgpa,
      cgpaScale: stateRef.current.scale,
      courseStudied: stateRef.current.courseStudied,
      gmail: stateRef.current.account?.email || "",
    });

    if (saveDebounceRef.current) {
      clearTimeout(saveDebounceRef.current);
    }
    saveDebounceRef.current = setTimeout(() => {
      void persistProfile(true);
    }, 1200);
  }

  async function handleClose() {
    if (saveDebounceRef.current) {
      clearTimeout(saveDebounceRef.current);
    }
    if (!isInitialLoading) {
      await persistProfile(false);
    }
    onClose();
  }

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        if (viewer) {
          setViewer(null);
        } else {
          void handleClose();
        }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [viewer, isInitialLoading]);

  useEffect(() => {
    return () => {
      if (saveDebounceRef.current) {
        clearTimeout(saveDebounceRef.current);
      }
      if (!stateRef.current.isInitialLoading) {
        const uid = getEffectiveUserId();
        const currentDocs: Record<string, ProfileDocument> = {};
        for (const [key, slot] of Object.entries(stateRef.current.files)) {
          if (slot && slot.url) {
            currentDocs[key] = {
              slotId: key,
              name: slot.name,
              url: slot.url,
              path: slot.path || "",
              kind: slot.kind,
              size: slot.size,
            };
          }
        }
        saveProfileDraft(uid, {
          userId: uid,
          firstName: stateRef.current.firstName,
          middleName: stateRef.current.middleName,
          lastName: stateRef.current.lastName,
          nationality: stateRef.current.nationality,
          cgpa: stateRef.current.cgpa,
          cgpaScale: stateRef.current.scale,
          courseStudied: stateRef.current.courseStudied,
          gmail: stateRef.current.account?.email || "",
          documents: currentDocs,
        });
      }
    };
  }, []);

  function openPicker(id: string) {
    setPendingSlot(id);
    fileInputRef.current?.click();
  }

  async function onFileChosen(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    const slotId = pendingSlot;
    event.target.value = "";
    setPendingSlot(null);
    if (!file || !slotId) return;

    const uid = getEffectiveUserId();
    const label = labelForSlot(slotId);
    toast.loading(`Uploading ${label}...`, { id: `doc-${slotId}` });

    try {
      const uploaded = await uploadUserDocument(uid, slotId, file);
      setFiles((current) => ({
        ...current,
        [slotId]: {
          file,
          url: uploaded.url,
          name: uploaded.name,
          kind: uploaded.kind,
          path: uploaded.path,
          size: uploaded.size,
        },
      }));
      toast.success(`${label} uploaded`, { id: `doc-${slotId}` });
      setTimeout(() => {
        void persistProfile(false);
      }, 50);
    } catch (err) {
      console.error("Document upload failed:", err);
      toast.error(
        err instanceof Error ? err.message : "Document upload failed",
        { id: `doc-${slotId}` }
      );
    }
  }

  async function removeFile(id: string) {
    const currentSlot = files[id];
    const label = labelForSlot(id);
    setFiles((current) => ({ ...current, [id]: null }));
    setViewer((current) => (current && files[id]?.url === current.url ? null : current));
    toast(`${label} removed`, { id: `doc-${id}-removed` });

    if (currentSlot?.path) {
      try {
        await deleteUserDocument(currentSlot.path);
      } catch (err) {
        console.warn("Storage deletion error:", err);
      }
    }

    setTimeout(() => {
      void persistProfile(false);
    }, 50);
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
      setTimeout(() => {
        void persistProfile(false);
      }, 50);
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
    setTimeout(() => {
      void persistProfile(false);
    }, 50);
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
        onChange={(e) => void onFileChosen(e)}
      />

      <div className="panel">
        <header className="panelHeader">
          <p>User Information</p>
          <IconItem
            size={32}
            icon={<X size={14} strokeWidth={1.5} />}
            aria-label="Close user information"
            onClick={() => void handleClose()}
          />
        </header>

        <section className="infoSection">
          <h2>Personal</h2>
          <div className="fieldGroup">
            <span className="fieldLabel">Name</span>
            <div className="nameRow">
              <FieldItem
                placeholder="First"
                autoComplete="given-name"
                name="given-name"
                value={firstName}
                disabled={isInitialLoading}
                onChange={(e) => {
                  setFirstName(e.target.value);
                  triggerAutoSave();
                }}
                onBlur={() => void persistProfile(true)}
              />
              <FieldItem
                placeholder="Middle"
                autoComplete="additional-name"
                name="additional-name"
                value={middleName}
                disabled={isInitialLoading}
                onChange={(e) => {
                  setMiddleName(e.target.value);
                  triggerAutoSave();
                }}
                onBlur={() => void persistProfile(true)}
              />
              <FieldItem
                placeholder="Last"
                autoComplete="family-name"
                name="family-name"
                value={lastName}
                disabled={isInitialLoading}
                onChange={(e) => {
                  setLastName(e.target.value);
                  triggerAutoSave();
                }}
                onBlur={() => void persistProfile(true)}
              />
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
                  disabled={isInitialLoading}
                  onChange={(event) => {
                    setNationality(event.target.value);
                    triggerAutoSave();
                  }}
                  onBlur={() => void persistProfile(true)}
                  onKeyDown={(event) => {
                    if (
                      (event.key === "Tab" || event.key === "Enter") &&
                      nationality &&
                      nationalitySuggestion
                    ) {
                      event.preventDefault();
                      setNationality(nationalitySuggestion);
                      triggerAutoSave();
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
                <FieldItem
                  placeholder="3.80"
                  inputMode="decimal"
                  value={cgpa}
                  disabled={isInitialLoading}
                  onChange={(e) => {
                    setCgpa(e.target.value);
                    triggerAutoSave();
                  }}
                  onBlur={() => void persistProfile(true)}
                />
                <div className="scalePicker" role="group" aria-label="CGPA scale">
                  {SCALES.map((value) => (
                    <ButtonItem
                      key={value}
                      size={24}
                      text={value}
                      state={scale === value ? "active" : "default"}
                      onClick={() => {
                        setScale(value);
                        setTimeout(() => void persistProfile(true), 10);
                      }}
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
                  disabled={isInitialLoading}
                  onChange={(event) => {
                    setCourseStudied(event.target.value);
                    triggerAutoSave();
                  }}
                  onBlur={() => void persistProfile(true)}
                  onKeyDown={(event) => {
                    if (
                      (event.key === "Tab" || event.key === "Enter") &&
                      courseStudied &&
                      courseStudiedSuggestion
                    ) {
                      event.preventDefault();
                      setCourseStudied(courseStudiedSuggestion);
                      triggerAutoSave();
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
                          onClick={() => void removeFile(slot.id)}
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
