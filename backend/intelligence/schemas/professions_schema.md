# Professions KB — entry schema (v1)

File: `professions_kb/professions.json` — a JSON array of entries. Each entry:

| Field           | Type            | Required | Notes |
|-----------------|-----------------|----------|-------|
| id              | string          | yes      | unique slug, e.g. `software_engineer` |
| name            | string          | yes      | display name, e.g. `Software Engineer` |
| category        | string          | yes      | e.g. `Technology`, `Healthcare`, `Finance`, `Government`, `Trades`, `Small Business`, `Creative`, `Education`, `Legal`, `Defence` |
| description     | string          | yes      | 2-3 sentences, plain language |
| entry_paths     | array of string | yes      | degrees / exams / skills that lead in, e.g. `["B.Tech CSE", "Self-taught + portfolio"]` |
| pros            | array of string | yes      | 3-6 honest advantages |
| cons            | array of string | yes      | 3-6 honest disadvantages — include REAL downsides (stress, saturation, pay ceilings, physical toll, instability). No entry may have empty cons. |
| salary_inr      | object          | yes      | `{"entry": "4-8 LPA", "experienced": "15-35 LPA", "note": "estimate"}` — ranges only, note ALWAYS "estimate" |
| demand_outlook  | string          | yes      | 1-2 lines on India demand trend |
| fit_notes       | string          | yes      | who tends to thrive / struggle here |
| typical_timeline| string          | yes      | e.g. `4-year B.Tech + 0-2 yrs experience to mid-level` |
| sources         | array of string | no       | URLs or publication names the salary/demand claims rest on |

Example:
```json
{
  "id": "tea_shop_owner",
  "name": "Tea Shop Owner",
  "category": "Small Business",
  "description": "Running a small tea stall or shop — one of the most common micro-businesses in India. Low entry barrier, income depends entirely on location and footfall.",
  "entry_paths": ["No formal degree needed", "FSSAI food licence", "Small capital Rs 20k-2L"],
  "pros": ["Very low entry barrier", "Daily cash flow", "Scales to multiple stalls", "No boss, own hours"],
  "cons": ["Long working hours, early mornings", "Income capped by location", "No job security or benefits", "Physically demanding, heat and standing all day"],
  "salary_inr": {"entry": "Rs 15k-40k/month", "experienced": "Rs 40k-1L+/month (multiple outlets)", "note": "estimate"},
  "demand_outlook": "Stable — tea demand is evergreen in India; premium/specialty stalls growing in cities.",
  "fit_notes": "Suits people comfortable with physical work, early hours, and customer interaction; hard for those wanting predictable salaried income.",
  "typical_timeline": "Immediate start possible; 1-3 years to stabilize a loyal customer base.",
  "sources": []
}
```

HARD RULES:
- Salaries are RANGES from researched sources, ALWAYS with `"note": "estimate"`. Never state a salary as a precise fact.
- Pros AND cons mandatory and balanced. If a profession is saturated, say so. If pay is low, say so.
- Never invent statistics ("92% of X..."). Qualitative, honest, sourced where possible.
- `id` globally unique.
