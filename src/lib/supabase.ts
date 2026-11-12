import { createClient } from "@supabase/supabase-js";

export const SUPABASE_URL =
  import.meta.env.VITE_SUPABASE_URL || "https://pcvkhuxliqcwravprdhn.supabase.co";

export const SUPABASE_ANON_KEY =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBjdmtodXhsaXFjd3JhdnByZGhuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMxMjQ5MTUsImV4cCI6MjEwODcwMDkxNX0.hfvpnyong-Jt4nTbEWS1DUoF4YI5PZRJ1D2B8wBErkE";

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  realtime: {
    params: {
      eventsPerSecond: 10,
    },
  },
});
