# Resources KB — entry schema (v1)

File: `resources_kb/resources.json` — a JSON array of entries. Each entry:

| Field      | Type    | Required | Notes |
|------------|---------|----------|-------|
| id         | string  | yes      | unique slug, e.g. `yt_physicswallah_11_12` |
| subject    | string  | yes      | e.g. `Physics`, `Data Structures`, `Accountancy` |
| level      | string  | yes      | one of: `class_6_8`, `class_9_10`, `class_11_12`, `UG`, `PG`, `skill` |
| stream     | string  | yes      | e.g. `science`, `commerce`, `arts`, `engineering_cse`, `engineering_other`, `medical_prep`, `law`, `upsc_govt`, `general` |
| type       | string  | yes      | one of: `youtube_channel`, `free_course`, `paid_course`, `book`, `community` |
| name       | string  | yes      | real name of the channel / course / book / community |
| url        | string  | yes      | must be VERIFIED: fetched with browser.open, HTTP 200, page content relevant to the named resource |
| url_verified | boolean | yes     | true only after a real fetch confirmed it |
| language   | string  | yes      | one of: `English`, `Hindi`, `Hinglish`, `other` |
| cost_inr   | number  | yes      | 0 if free; actual rupee price if paid (from the provider's own page) |
| notes      | string  | yes      | 1-2 lines: who it's for, what's good, any caveat |

Example:
```json
{
  "id": "yt_physicswallah_11_12",
  "subject": "Physics",
  "level": "class_11_12",
  "stream": "science",
  "type": "youtube_channel",
  "name": "Physics Wallah",
  "url": "https://www.youtube.com/@PhysicsWallah",
  "url_verified": true,
  "language": "Hinglish",
  "cost_inr": 0,
  "notes": "Hugely popular for JEE/NEET physics in Hindi/Hinglish. Free lectures; paid batches exist separately."
}
```

HARD RULES:
- NEVER invent a URL, channel name, course name, or price. If you are not sure it exists, verify by fetching. If you cannot verify it, DROP the entry.
- Prefer official/canonical URLs (youtube.com/@handle, swayam.gov.in, nptel.ac.in, provider's own site).
- Duplicates across parts files are resolved at merge by `id` — keep ids globally unique and descriptive.
