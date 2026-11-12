const STORAGE_KEY = "schol.google-account";
const SCRIPT_SRC = "https://accounts.google.com/gsi/client";

export type GoogleAccount = {
  email: string;
  name: string;
  accessToken: string;
};

type TokenClient = {
  requestAccessToken: (override?: { prompt?: string }) => void;
};

type GoogleIdentity = {
  accounts: {
    oauth2: {
      initTokenClient: (config: {
        client_id: string;
        scope: string;
        callback: (response: { access_token?: string; error?: string }) => void;
      }) => TokenClient;
      revoke: (token: string, done: () => void) => void;
    };
  };
};

declare global {
  interface Window {
    google?: GoogleIdentity;
  }
}

const SCOPES = [
  "openid",
  "email",
  "profile",
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/calendar.events",
].join(" ");

export function loadStoredAccount(): GoogleAccount | null {
  // Check if returning from Google OAuth redirect with parameters
  if (typeof window !== "undefined") {
    try {
      const params = new URLSearchParams(window.location.search);
      if (params.get("google") === "connected") {
        const email = params.get("email") || "";
        const name = params.get("name") || email;
        const account: GoogleAccount = { email, name, accessToken: "" };
        saveAccount(account);
        const cleanUrl = window.location.origin + window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);
        return account;
      }
    } catch {
      // Ignore URL parsing errors
    }
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as GoogleAccount) : null;
  } catch {
    return null;
  }
}

function saveAccount(account: GoogleAccount | null) {
  if (!account) {
    localStorage.removeItem(STORAGE_KEY);
    return;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(account));
}

function loadGis(): Promise<GoogleIdentity> {
  if (window.google?.accounts?.oauth2) return Promise.resolve(window.google);
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${SCRIPT_SRC}"]`);
    if (existing) {
      existing.addEventListener("load", () => {
        if (window.google) resolve(window.google);
        else reject(new Error("Google Identity failed to load"));
      });
      return;
    }
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      if (window.google) resolve(window.google);
      else reject(new Error("Google Identity failed to load"));
    };
    script.onerror = () => reject(new Error("Google Identity failed to load"));
    document.head.appendChild(script);
  });
}

async function profileFromToken(accessToken: string) {
  const response = await fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) throw new Error("Could not read Google profile");
  const data = (await response.json()) as { email?: string; name?: string };
  if (!data.email) throw new Error("Google did not return an email");
  return { email: data.email, name: data.name ?? data.email };
}

export async function connectGoogleAccount(): Promise<GoogleAccount> {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;
  const authServerUrl = import.meta.env.VITE_AUTH_SERVER_URL || "http://localhost:3000";

  // 1. Try Google Identity Services client-side popup if VITE_GOOGLE_CLIENT_ID is set
  if (clientId) {
    try {
      const google = await loadGis();
      return await new Promise<GoogleAccount>((resolve, reject) => {
        const client = google.accounts.oauth2.initTokenClient({
          client_id: clientId,
          scope: SCOPES,
          callback: async (response) => {
            if (!response.access_token) {
              reject(new Error(response.error ?? "Google sign-in was cancelled"));
              return;
            }
            try {
              const profile = await profileFromToken(response.access_token);
              const account = { ...profile, accessToken: response.access_token };
              saveAccount(account);
              resolve(account);
            } catch (error) {
              reject(error);
            }
          },
        });
        client.requestAccessToken({ prompt: "consent" });
      });
    } catch (gisError) {
      console.warn("Client-side GIS failed or blocked, falling back to auth server:", gisError);
    }
  }

  // 2. Fallback to auth server flow (opens OAuth endpoint)
  const currentUrl = window.location.href;
  window.location.href = `${authServerUrl}/auth/google?returnTo=${encodeURIComponent(currentUrl)}`;

  return new Promise(() => {});
}

export async function disconnectGoogleAccount(account: GoogleAccount | null) {
  if (account?.accessToken && window.google?.accounts.oauth2) {
    await new Promise<void>((resolve) => {
      window.google?.accounts.oauth2.revoke(account.accessToken, resolve);
    });
  }

  // Also call backend disconnect if available
  const authServerUrl = import.meta.env.VITE_AUTH_SERVER_URL || "http://localhost:3000";
  try {
    await fetch(`${authServerUrl}/auth/disconnect`, {
      method: "POST",
      credentials: "include",
    });
  } catch {
    // Ignore backend disconnect errors if server is offline
  }

  saveAccount(null);
}

export async function syncCalendarEvents(
  account: GoogleAccount,
  events: { title: string; date: string }[]
) {
  if (account.accessToken) {
    // Direct client-side sync using access token
    await Promise.all(
      events.map((event) =>
        fetch(
          "https://www.googleapis.com/calendar/v3/calendars/primary/events",
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${account.accessToken}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              summary: event.title,
              description: "Scholarship deadline from Schol",
              start: { date: event.date },
              end: { date: event.date },
            }),
          }
        )
      )
    );
  } else {
    // Server-side session sync
    const authServerUrl = import.meta.env.VITE_AUTH_SERVER_URL || "http://localhost:3000";
    const response = await fetch(`${authServerUrl}/api/calendar/sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ events }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || "Failed to sync calendar events via server.");
    }
  }
}
