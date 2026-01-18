# function.json - Schedule Configuration

This file controls when the Azure Function runs automatically.

## Current Schedule

```json
"schedule": "0 0 12 * * 1-5"
```

This means: **7:00 AM Toronto time, Monday through Friday**

---

## Understanding the CRON Expression

Azure Functions use **NCRONTAB format** with 6 fields:

```
"0 0 12 * * 1-5"
 │ │ │  │ │ │
 │ │ │  │ │ └─ Day of week (1-5 = Monday-Friday)
 │ │ │  │ └─── Month (* = every month)
 │ │ │  └───── Day of month (* = every day)
 │ │ └──────── Hour (12 = 12:00 UTC = 7:00 AM Toronto)
 │ └────────── Minute (0)
 └──────────── Second (0)
```

**Important:** Azure uses **UTC timezone**, not Toronto time.

---

## How to Change the Time

To change when the report runs, modify the **hour** value (third number).

### Time Conversion Table

| Toronto Time | UTC Hour | Schedule Expression |
|--------------|----------|---------------------|
| 6:00 AM | 11 | `"0 0 11 * * 1-5"` |
| 7:00 AM | 12 | `"0 0 12 * * 1-5"` |
| 8:00 AM | 13 | `"0 0 13 * * 1-5"` |
| 9:00 AM | 14 | `"0 0 14 * * 1-5"` |
| 10:00 AM | 15 | `"0 0 15 * * 1-5"` |

### Conversion Formula

- **Winter (EST):** Toronto hour + 5 = UTC hour
- **Summer (EDT):** Toronto hour + 4 = UTC hour

---

## Common Examples

| Goal | Schedule Expression |
|------|---------------------|
| 7:00 AM, Mon-Fri | `"0 0 12 * * 1-5"` |
| 8:30 AM, Mon-Fri | `"0 30 13 * * 1-5"` |
| 9:00 AM, every day | `"0 0 14 * * *"` |
| 7:00 AM, only Monday | `"0 0 12 * * 1"` |

---

## Day of Week Values

| Day | Value |
|-----|-------|
| Sunday | 0 |
| Monday | 1 |
| Tuesday | 2 |
| Wednesday | 3 |
| Thursday | 4 |
| Friday | 5 |
| Saturday | 6 |

---

## After Making Changes

After modifying `function.json`, you must **redeploy** the function to Azure for changes to take effect.
