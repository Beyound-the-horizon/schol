# Scholarship AI Intelligence API Documentation

The **Scholarship AI Intelligence API** is the AI reasoning layer that sits on top of your scholarship database. Built with **FastAPI**, **Google Gemini 3.8 Flash**, and **Supabase PostgreSQL**, it analyzes raw scholarship data to generate structured, actionable application roadmaps for students.

---

## 1. Quick Start & Base URLs

### Base URLs
- **Local Development**: `http://localhost:8000`
- **Vercel Production**: `https://<your-vercel-deployment>.vercel.app`
- **API Prefix**: All core scholarship routes are prefixed with `/api/v1`.

### Interactive Documentation
FastAPI provides automatic interactive API documentation:
- **Swagger UI**: [`/docs`](http://localhost:8000/docs) (test endpoints directly in your browser)
- **ReDoc**: [`/redoc`](http://localhost:8000/redoc) (clean, human-readable specification)

### CORS Policy
Cross-Origin Resource Sharing is enabled for all origins (`*`), allowing your React frontend ([`schol-tau.vercel.app`](https://schol-tau.vercel.app/)) and local Vite development (`localhost:5173`) to call the API without proxy or CORS issues.

---

## 2. API Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Root service discovery & documentation links |
| `GET` | `/health` | Service health status and active Gemini model |
| `GET` | `/api/v1/scholarships` | Paginated list of all indexed scholarships |
| `GET` | `/api/v1/scholarships/{id}` | Detailed database record for a single scholarship |
| `GET` | `/api/v1/scholarships/{id}/guidance` | **Core AI feature**: Generated/cached application roadmap |
| `POST` | `/api/v1/guidance/preview` | Generate AI guidance on arbitrary raw data on the fly |

---

## 3. Detailed Endpoint Reference

### `GET /`

**Summary**: Service Discovery & Status  
Returns entrypoint metadata and links to documentation.

#### Response (`200 OK`)
```json
{
  "message": "Scholarship AI Intelligence API",
  "docs_url": "/docs",
  "health_url": "/health",
  "api_prefix": "/api/v1"
}
```

---

### `GET /health`

**Summary**: System Health Check  
Verifies whether the FastAPI backend is operational and identifies the configured AI model.

#### Response (`200 OK`)
```json
{
  "status": "healthy",
  "service": "Scholarship AI Intelligence API",
  "model": "gemini-3.8-flash",
  "api_version": "v1"
}
```

---

### `GET /api/v1/scholarships`

**Summary**: List Indexed Scholarships  
Retrieves scholarships stored in the Supabase PostgreSQL database with pagination.

#### Query Parameters
| Parameter | Type | Default | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `limit` | integer | `20` | `1 <= limit <= 100` | Maximum number of records to return |
| `offset` | integer | `0` | `offset >= 0` | Number of records to skip |

#### Example Request
```http
GET /api/v1/scholarships?limit=2&offset=0
```

#### Response (`200 OK`)
```json
{
  "count": 2,
  "limit": 2,
  "offset": 0,
  "scholarships": [
    {
      "id": 1,
      "name": "Commonwealth Master's Scholarships",
      "provider": "Commonwealth Scholarship Commission (CSC)",
      "host_country": "United Kingdom",
      "degree_level": "Master's",
      "funding_type": "Fully Funded",
      "official_url": "https://cscuk.fcdo.gov.uk/scholarships/commonwealth-masters-scholarships/",
      "deadline": "2026-10-15",
      "is_ai_guidance_cached": true
    }
  ]
}
```

---

### `GET /api/v1/scholarships/{scholarship_id}`

**Summary**: Get Single Scholarship Raw Data  
Retrieves the complete database record for a specific scholarship, including raw scrape attributes, eligibility criteria, and any pre-existing cached guidance.

#### Path Parameters
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `scholarship_id` | integer | **Yes** | The database primary key ID |

#### Example Request
```http
GET /api/v1/scholarships/1
```

#### Responses
- **`200 OK`**: Returns the complete record dictionary.
- **`404 Not Found`**:
  ```json
  {
    "detail": "Scholarship with ID 9999 not found in database."
  }
  ```

---

### `GET /api/v1/scholarships/{scholarship_id}/guidance`

**Summary**: Get AI Application Guidance & Nested Apply URL  
This is the **primary AI endpoint**. It resolves the scholarship into an actionable step-by-step roadmap:
1. **Direct Account Portal**: Locates the nested registration/apply URL instead of a generic landing page.
2. **Application Architecture**: Classifies the scholarship into 1 of 4 application schemes.
3. **Phased Roadmap**: Sequenced step-by-step actions with prerequisites and common disqualification pitfalls.
4. **Intelligent Timeline**: Estimates opening windows, deadlines, and intake cycles when official dates are not yet announced.
5. **Essay & Word Count Specs**: Extracts exact word limits, character caps, and scoring criteria for motivation letters.

> [!NOTE]
> **Intelligent Caching**: Once Gemini generates guidance for a scholarship, it is saved directly into the Supabase database (`scholarships.ai_guidance`). Subsequent requests return instantly without calling Gemini. Use `refresh=true` to force re-analysis.

#### Path & Query Parameters
| Parameter | In | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `scholarship_id` | path | integer | *(required)* | ID of the scholarship |
| `refresh` | query | boolean | `false` | When `true`, ignores the cache, calls Gemini again, and updates the database |

#### Example Request
```http
GET /api/v1/scholarships/1/guidance?refresh=false
```

#### Response Structure (`200 OK`)
```json
{
  "scholarship_id": 1,
  "scholarship_name": "Commonwealth Master's Scholarships",
  "summary_explanation": "The Commonwealth Master's Scholarship is a dual-application process requiring applicants to apply through a national nominating agency or organization as well as the CSC online application system, alongside securing admission to an eligible UK university.",
  "application_pattern": "DUAL_APPLICATION",
  "total_applications_required": 2,
  "active_apply_link": {
    "primary_apply_url": "https://fs29.formsite.com/m3nCYq/CSC-Masters-2026/index.html",
    "portal_name": "CSC Online Application System (Formsite / SmartSimple)",
    "is_direct_account_creation": true,
    "secondary_apply_url": "https://www.ox.ac.uk/admissions/graduate/applying-to-oxford",
    "navigation_instructions": "Access the primary portal, click 'Register New Account', select 'Commonwealth Master's', and note down your candidate ID before submitting your national nominating agency form."
  },
  "workflow_phases": [
    {
      "phase_number": 1,
      "title": "Phase 1: Secure University Admission & Select Nominating Body",
      "target_entity": "UK Partner University / National Nominating Agency",
      "portal_url": null,
      "prerequisites": [
        "Undergraduate academic transcript (minimum 2:1 honours)",
        "Proof of citizenship in an eligible Commonwealth country"
      ],
      "action_items": [
        "Apply to at least two participating UK university courses.",
        "Check your home country's nominating agency guidelines and their internal deadline (often 2-4 weeks earlier than CSC)."
      ],
      "pitfalls_to_avoid": [
        "Failing to apply through the national nominating agency will automatically disqualify your CSC submission.",
        "Applying for a university course not covered by CSC funding."
      ]
    },
    {
      "phase_number": 2,
      "title": "Phase 2: Complete the CSC Central Online Application",
      "target_entity": "Commonwealth Scholarship Commission",
      "portal_url": "https://cscuk.fcdo.gov.uk/apply/",
      "prerequisites": [
        "Two institutional referee letters",
        "Personal development impact statement"
      ],
      "action_items": [
        "Upload verified academic certificates.",
        "Draft and paste the 4-part Development Impact statement."
      ],
      "pitfalls_to_avoid": [
        "Referee letters not submitted directly by referees before the cutoff.",
        "Exceeding specified word limits."
      ]
    }
  ],
  "timeline": {
    "status": "OPEN",
    "is_estimated": false,
    "confirmed_open_date": "2026-09-05",
    "confirmed_deadline": "2026-10-15",
    "estimated_open_window": "Early September 2026",
    "estimated_deadline_window": "Mid October 2026",
    "typical_duration_weeks": 6,
    "timing_advice": "Request referee recommendations at least 4 weeks before the deadline, as the portal closes strictly at 16:00 BST."
  },
  "essay_requirements": [
    {
      "prompt_title": "Development Impact Statement",
      "min_word_count": 250,
      "max_word_count": 500,
      "max_character_count": null,
      "sub_questions": [
        "How will your proposed study relate to development priorities in your home country?",
        "How will you apply your new skills upon returning home?"
      ],
      "key_scoring_criteria": [
        "Direct alignment with UN Sustainable Development Goals (SDGs)",
        "Measurable socio-economic impact plan within 5 years of graduation"
      ],
      "recommended_structure": [
        "Paragraph 1: National problem statement and data.",
        "Paragraph 2: Course modules directly addressing this bottleneck.",
        "Paragraph 3: Concrete post-graduation implementation plan."
      ]
    }
  ],
  "general_tips": [
    "Contact your national nominating agency early as their internal deadlines can be earlier than the CSC portal deadline.",
    "Ensure your referee upload links are checked frequently; late referees lead to disqualification."
  ],
  "generated_at": "2026-11-19T13:45:00Z"
}
```

---

### `POST /api/v1/guidance/preview`

**Summary**: On-the-Fly AI Guidance Preview  
Generates full AI guidance for custom or newly scraped data without requiring the scholarship to exist in the database.

#### Request Body (`application/json`)
```json
{
  "scholarship_name": "Chevening Scholarships",
  "provider": "Foreign, Commonwealth & Development Office (FCDO)",
  "host_country": "United Kingdom",
  "official_url": "https://www.chevening.org/scholarships/",
  "other_eligibility": "Minimum 2 years of work experience (2,800 hours), undergraduate degree.",
  "essay_requirements": "4 essays: Leadership & Influence, Networking, Studying in the UK, Career Plan.",
  "required_documents": [
    "Academic transcripts",
    "Two reference letters",
    "Valid passport"
  ]
}
```

#### Response (`200 OK`)
Returns the exact same `ScholarshipGuidance` schema as above, generated in real time.

---

## 4. Key Data Models & Enums

### Application Patterns (`ApplicationPattern`)
The AI categorizes every scholarship into one of four distinct patterns:

| Pattern Enum | Applications Required | Description |
| :--- | :---: | :--- |
| `SINGLE_PORTAL` | 1 | You apply entirely through one scholarship portal (e.g. create account, submit essays, select eligible universities inside the portal). |
| `COURSE_FIRST_AUTOMATIC` | 1 | You apply solely for the university course; the university automatically considers eligible applicants for the scholarship with no separate form. |
| `COURSE_FIRST_NOMINATED` | 1 + nomination | You apply to the university course first. If admitted, the university department selects and nominates top candidates to the scholarship organization. |
| `DUAL_APPLICATION` | 2 | You must submit **two separate applications**: one directly to the university for course admission, and one directly to the scholarship foundation/government body. |

### Timeline Statuses
- `OPEN`: Applications are actively being accepted right now.
- `UPCOMING`: Applications will open soon; preparing documents now is recommended.
- `CLOSED`: The current intake cycle has finished; refer to `estimated_open_window` for the next cycle.
- `ROLLING`: Applications are reviewed on an ongoing basis until quotas are filled.

---

## 5. Integration Code Examples

### Frontend Integration (React / TypeScript)

```typescript
// services/scholarshipApi.ts
const BASE_URL = 'https://<your-api-url>.vercel.app/api/v1';

export interface ScholarshipGuidance {
  scholarship_id: number;
  scholarship_name: string;
  summary_explanation: string;
  application_pattern: 'SINGLE_PORTAL' | 'COURSE_FIRST_AUTOMATIC' | 'COURSE_FIRST_NOMINATED' | 'DUAL_APPLICATION';
  total_applications_required: number;
  active_apply_link: {
    primary_apply_url: string;
    portal_name: string;
    is_direct_account_creation: boolean;
    secondary_apply_url?: string;
    navigation_instructions: string;
  };
  timeline: {
    status: 'OPEN' | 'UPCOMING' | 'CLOSED' | 'ROLLING';
    estimated_open_window: string;
    estimated_deadline_window: string;
    timing_advice: string;
  };
  workflow_phases: Array<{
    phase_number: number;
    title: string;
    action_items: string[];
    pitfalls_to_avoid: string[];
  }>;
  essay_requirements: Array<{
    prompt_title: string;
    min_word_count?: number;
    max_word_count?: number;
    sub_questions: string[];
  }>;
}

export async function fetchGuidance(scholarshipId: number, forceRefresh = false): Promise<ScholarshipGuidance> {
  const url = `${BASE_URL}/scholarships/${scholarshipId}/guidance?refresh=${forceRefresh}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load guidance: ${response.statusText}`);
  }
  return response.json();
}
```

---

### Python Integration (`requests`)

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. List scholarships
resp = requests.get(f"{BASE_URL}/scholarships", params={"limit": 10})
scholarships = resp.json()["scholarships"]

# 2. Get AI application guidance for scholarship ID 1
guidance = requests.get(f"{BASE_URL}/scholarships/1/guidance").json()

print(f"Portal: {guidance['active_apply_link']['portal_name']}")
print(f"Direct URL: {guidance['active_apply_link']['primary_apply_url']}")
print(f"Pattern: {guidance['application_pattern']}")
```

---

### cURL

```bash
# Check service health
curl -s http://localhost:8000/health

# Fetch paginated list
curl -s "http://localhost:8000/api/v1/scholarships?limit=5"

# Fetch AI guidance
curl -s "http://localhost:8000/api/v1/scholarships/1/guidance"

# Force refresh Gemini guidance
curl -s "http://localhost:8000/api/v1/scholarships/1/guidance?refresh=true"
```

```