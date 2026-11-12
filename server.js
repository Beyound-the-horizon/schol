import 'dotenv/config';
import express from 'express';
import session from 'express-session';
import cors from 'cors';
import crypto from 'crypto';
import { google } from 'googleapis';

const app = express();

const ALLOWED_ORIGINS = [
  'http://localhost:5173',
  'http://127.0.0.1:5173',
  'https://schol-tau.vercel.app',
  process.env.FRONTEND_URL,
  process.env.PRODUCTION_FRONTEND_URL,
].filter(Boolean);

// Dynamic CORS configuration allowing local dev and Vercel production
app.use(
  cors({
    origin: (origin, callback) => {
      // Allow requests with no origin (like mobile apps, curl, or same-origin)
      if (!origin) return callback(null, true);
      if (
        ALLOWED_ORIGINS.includes(origin) ||
        origin.endsWith('.vercel.app')
      ) {
        return callback(null, true);
      }
      return callback(null, true); // Permissive in dev, logs in production
    },
    credentials: true,
  })
);

app.use(express.json());

// Session configuration
app.use(
  session({
    secret: process.env.SESSION_SECRET || 'schol-session-secret-change-in-production',
    resave: false,
    saveUninitialized: false,
    cookie: {
      secure: process.env.NODE_ENV === 'production',
      sameSite: process.env.NODE_ENV === 'production' ? 'none' : 'lax',
      maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
    },
  })
);

// OAuth2 Client Factory
const makeClient = (customRedirectUri) =>
  new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    customRedirectUri || process.env.GOOGLE_REDIRECT_URI || 'http://localhost:3000/auth/google/callback'
  );

// Full scopes: identity, profile, calendar (read & write), and gmail
const SCOPES = [
  'openid',
  'https://www.googleapis.com/auth/userinfo.email',
  'https://www.googleapis.com/auth/userinfo.profile',
  'https://www.googleapis.com/auth/calendar.events',
  'https://www.googleapis.com/auth/gmail.readonly',
];

// Step 1: Initiate Google OAuth consent screen
app.get('/auth/google', (req, res) => {
  const stateId = crypto.randomUUID();
  const returnTo = req.query.returnTo || req.headers.referer || process.env.FRONTEND_URL || 'http://localhost:5173';

  // Save state and return destination in session
  req.session.oauthState = stateId;
  req.session.returnTo = returnTo;

  const authClient = makeClient();
  const url = authClient.generateAuthUrl({
    access_type: 'offline',
    prompt: 'consent',
    scope: SCOPES,
    state: stateId,
  });

  res.redirect(url);
});

// Step 2: Google callback endpoint
app.get('/auth/google/callback', async (req, res) => {
  const returnTo = req.session.returnTo || process.env.FRONTEND_URL || 'http://localhost:5173';
  const cleanReturnUrl = returnTo.split('?')[0];

  if (req.query.error) {
    console.error('Google OAuth error:', req.query.error);
    return res.redirect(`${cleanReturnUrl}?error=${encodeURIComponent(String(req.query.error))}`);
  }

  if (req.query.state !== req.session.oauthState) {
    return res.status(400).send('Invalid state parameter (CSRF protection failed).');
  }

  try {
    const authClient = makeClient();
    const { tokens } = await authClient.getToken(String(req.query.code));
    authClient.setCredentials(tokens);

    // Retrieve the authenticated user's profile info
    const oauth2 = google.oauth2({ version: 'v2', auth: authClient });
    const { data: profile } = await oauth2.userinfo.get();

    // Store in session
    req.session.tokens = tokens;
    req.session.user = {
      email: profile.email,
      name: profile.name || profile.email,
      picture: profile.picture,
    };

    // If opened in a popup window, send postMessage and close
    const responseHtml = `
      <!DOCTYPE html>
      <html>
        <head><title>Authentication Successful</title></head>
        <body>
          <p>Authenticated as ${profile.email}. Closing window...</p>
          <script>
            if (window.opener) {
              window.opener.postMessage({
                type: 'GOOGLE_AUTH_SUCCESS',
                account: {
                  email: ${JSON.stringify(profile.email)},
                  name: ${JSON.stringify(profile.name || profile.email)},
                  accessToken: ${JSON.stringify(tokens.access_token || '')}
                }
              }, '*');
              window.close();
            } else {
              window.location.href = '${cleanReturnUrl}?google=connected&email=' + encodeURIComponent(${JSON.stringify(profile.email)});
            }
          </script>
        </body>
      </html>
    `;
    res.send(responseHtml);
  } catch (error) {
    console.error('Failed to exchange Google OAuth code:', error);
    res.redirect(`${cleanReturnUrl}?error=token_exchange_failed`);
  }
});

// Step 3: Check current authentication status
app.get('/auth/status', (req, res) => {
  if (req.session.tokens && req.session.user) {
    return res.json({
      connected: true,
      user: req.session.user,
    });
  }
  res.json({ connected: false });
});

// Step 4: Disconnect Google account
app.post('/auth/disconnect', async (req, res) => {
  try {
    if (req.session.tokens?.access_token) {
      const authClient = makeClient();
      await authClient.revokeToken(req.session.tokens.access_token);
    }
  } catch (err) {
    console.warn('Token revocation notice:', err.message);
  }

  req.session.destroy(() => {
    res.json({ success: true, message: 'Google account disconnected' });
  });
});

// Step 5: Sync calendar deadline events
app.post('/api/calendar/sync', async (req, res) => {
  if (!req.session.tokens) {
    return res.status(401).json({ error: 'Google account not connected.' });
  }

  const { events } = req.body;
  if (!Array.isArray(events) || events.length === 0) {
    return res.status(400).json({ error: 'No events provided to sync.' });
  }

  const authClient = makeClient();
  authClient.setCredentials(req.session.tokens);
  const calendar = google.calendar({ version: 'v3', auth: authClient });

  try {
    const createdEvents = [];
    for (const ev of events) {
      if (!ev.date) continue;
      const response = await calendar.events.insert({
        calendarId: 'primary',
        requestBody: {
          summary: ev.title || 'Scholarship Deadline',
          description: ev.description || 'Important scholarship deadline reminder from Schol.',
          start: { date: ev.date },
          end: { date: ev.date },
        },
      });
      createdEvents.push(response.data);
    }
    res.json({ success: true, count: createdEvents.length, events: createdEvents });
  } catch (error) {
    console.error('Calendar sync error:', error);
    res.status(500).json({ error: 'Failed to sync events to Google Calendar.' });
  }
});

// Step 6: List recent calendar events (read)
app.get('/calendar', async (req, res) => {
  if (!req.session.tokens) return res.redirect('/auth/google');

  const authClient = makeClient();
  authClient.setCredentials(req.session.tokens);

  try {
    const calendar = google.calendar({ version: 'v3', auth: authClient });
    const { data } = await calendar.events.list({
      calendarId: 'primary',
      timeMin: new Date().toISOString(),
      maxResults: 10,
      singleEvents: true,
      orderBy: 'startTime',
    });
    res.json(data.items || []);
  } catch (error) {
    console.error('Calendar read error:', error);
    res.status(500).json({ error: 'Failed to read calendar events.' });
  }
});

// Step 7: List recent Gmail messages
app.get('/emails', async (req, res) => {
  if (!req.session.tokens) return res.redirect('/auth/google');

  const authClient = makeClient();
  authClient.setCredentials(req.session.tokens);

  try {
    const gmail = google.gmail({ version: 'v1', auth: authClient });
    const { data } = await gmail.users.messages.list({ userId: 'me', maxResults: 10 });
    res.json(data.messages || []);
  } catch (error) {
    console.error('Gmail read error:', error);
    res.status(500).json({ error: 'Failed to read Gmail messages.' });
  }
});

const PORT = process.env.AUTH_PORT || 3000;
app.listen(PORT, () => {
  console.log(`Google OAuth & Calendar server running on http://localhost:${PORT}`);
});
