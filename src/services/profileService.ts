/**
 * User Profile Persistence Service
 * Handles Supabase database upserts, localStorage fallback drafts,
 * and Supabase Storage uploads for user documents.
 */

import { supabase } from "../lib/supabase";
import { loadStoredAccount } from "../lib/googleAccount";

export type ProfileDocument = {
  slotId: string;
  name: string;
  url: string;
  path: string;
  kind: "image" | "pdf" | "file";
  size?: number;
};

export type UserProfile = {
  userId: string;
  firstName: string;
  middleName: string;
  lastName: string;
  nationality: string;
  cgpa: string;
  cgpaScale: string;
  courseStudied: string;
  gmail: string;
  documents: Record<string, ProfileDocument>;
  updatedAt?: string;
};

const LOCAL_USER_ID_KEY = "schol.user-id";
const DRAFT_KEY_PREFIX = "schol.profile-draft.";

/**
 * Returns the stable user ID.
 * Uses Google account email if signed in, otherwise a persistent device ID.
 */
export function getEffectiveUserId(): string {
  const account = loadStoredAccount();
  if (account?.email) {
    return account.email;
  }
  let localId = localStorage.getItem(LOCAL_USER_ID_KEY);
  if (!localId) {
    localId = `anon_${crypto.randomUUID()}`;
    localStorage.setItem(LOCAL_USER_ID_KEY, localId);
  }
  return localId;
}

/**
 * Save draft to localStorage as immediate offline / network fallback.
 */
export function saveProfileDraft(userId: string, data: Partial<UserProfile>): void {
  try {
    localStorage.setItem(`${DRAFT_KEY_PREFIX}${userId}`, JSON.stringify(data));
  } catch (err) {
    console.warn("Could not save profile draft to localStorage:", err);
  }
}

/**
 * Load draft from localStorage fallback.
 */
export function loadProfileDraft(userId: string): Partial<UserProfile> | null {
  try {
    const raw = localStorage.getItem(`${DRAFT_KEY_PREFIX}${userId}`);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/**
 * Clear draft from localStorage after successful save.
 */
export function clearProfileDraft(userId: string): void {
  try {
    localStorage.removeItem(`${DRAFT_KEY_PREFIX}${userId}`);
  } catch (err) {
    console.warn("Could not clear profile draft:", err);
  }
}

/**
 * Fetch profile from Supabase with fallback to localStorage draft.
 */
export async function fetchUserProfile(userId: string): Promise<UserProfile | null> {
  try {
    const { data, error } = await supabase
      .from("user_profiles")
      .select("*")
      .eq("user_id", userId)
      .maybeSingle();

    if (error) {
      console.warn("Supabase fetch profile error, checking draft:", error);
      const draft = loadProfileDraft(userId);
      return draft ? (draft as UserProfile) : null;
    }

    if (data) {
      const profile: UserProfile = {
        userId: data.user_id,
        firstName: data.first_name || "",
        middleName: data.middle_name || "",
        lastName: data.last_name || "",
        nationality: data.nationality || "",
        cgpa: data.cgpa || "",
        cgpaScale: data.cgpa_scale || "5.0",
        courseStudied: data.course_studied || "",
        gmail: data.gmail || "",
        documents: data.documents || {},
        updatedAt: data.updated_at,
      };
      return profile;
    }

    // No remote record yet, return local draft if present
    const draft = loadProfileDraft(userId);
    return draft ? (draft as UserProfile) : null;
  } catch (err) {
    console.warn("Failed to fetch user profile, falling back to draft:", err);
    const draft = loadProfileDraft(userId);
    return draft ? (draft as UserProfile) : null;
  }
}

/**
 * Upsert user profile to Supabase database and clear local draft on success.
 */
export async function saveUserProfile(profile: UserProfile): Promise<void> {
  // Save local draft first in case of network interruption
  saveProfileDraft(profile.userId, profile);

  const payload = {
    user_id: profile.userId,
    first_name: profile.firstName,
    middle_name: profile.middleName,
    last_name: profile.lastName,
    nationality: profile.nationality,
    cgpa: profile.cgpa,
    cgpa_scale: profile.cgpaScale,
    course_studied: profile.courseStudied,
    gmail: profile.gmail,
    documents: profile.documents,
    updated_at: new Date().toISOString(),
  };

  const { error } = await supabase
    .from("user_profiles")
    .upsert(payload, { onConflict: "user_id" });

  if (error) {
    throw new Error(`Failed to save profile to database: ${error.message}`);
  }

  // Clear local draft now that database has the authoritative state
  clearProfileDraft(profile.userId);
}

/**
 * Upload a document file to Supabase Storage bucket 'user-documents'.
 * Returns the public URL and file path to store in profile.documents.
 */
export async function uploadUserDocument(
  userId: string,
  slotId: string,
  file: File
): Promise<ProfileDocument> {
  const fileExt = file.name.split(".").pop() || "bin";
  const sanitizedSlot = slotId.replace(/[^a-zA-Z0-9_-]/g, "");
  const sanitizedUserId = userId.replace(/[^a-zA-Z0-9@._-]/g, "_");
  const filePath = `${sanitizedUserId}/${sanitizedSlot}_${Date.now()}.${fileExt}`;

  const { error: uploadError } = await supabase.storage
    .from("user-documents")
    .upload(filePath, file, {
      cacheControl: "3600",
      upsert: true,
    });

  if (uploadError) {
    throw new Error(`Upload failed: ${uploadError.message}`);
  }

  const { data: publicUrlData } = supabase.storage
    .from("user-documents")
    .getPublicUrl(filePath);

  const kind: "image" | "pdf" | "file" = file.type.startsWith("image/")
    ? "image"
    : file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")
    ? "pdf"
    : "file";

  return {
    slotId,
    name: file.name,
    url: publicUrlData.publicUrl,
    path: filePath,
    kind,
    size: file.size,
  };
}

/**
 * Delete a document from Supabase Storage bucket 'user-documents'.
 */
export async function deleteUserDocument(path: string): Promise<void> {
  if (!path) return;
  const { error } = await supabase.storage.from("user-documents").remove([path]);
  if (error) {
    console.warn("Could not delete file from Supabase storage:", error);
  }
}
