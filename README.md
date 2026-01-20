# Brevo CRM Daily Automation

Automated daily reporting system that extracts CRM activity from Brevo, generates AI-powered executive summaries using OpenAI model, and delivers formatted reports to Microsoft Teams.

## Features

- **Automated Data Extraction**: Pulls last 24 hours of CRM activity from Brevo API (72 hours on Mondays)
- **Intelligent Filtering**:
  - Company-level notes only (excludes contact and deal notes)
  - Filters out AI-generated notes automatically
  - Differentiates new deals from updated deals based on timestamps
- **AI-Powered Summaries**: Generates executive-level summaries using OpenAI models
- **Teams Integration**: Delivers formatted reports via Microsoft Teams webhook
- **Timezone-Aware**: Handles Toronto (EST/EDT) to UTC conversions automatically
- **Mock Data Support**: Test locally without hitting real APIs
- **Error Resilience**: Sends partial reports with error notices when APIs fail
- **Production-Ready**: Comprehensive logging and error handling

## Project Structure

```
CRM-Automation/
├── DailyReportFunction/
│   ├── __init__.py              # Main Azure Function handler
│   └── function.json            # Timer trigger configuration
├── shared/
│   ├── brevo_client.py          # Brevo API integration
│   ├── openai_client.py         # OpenAI integration
│   ├── teams_client.py          # Microsoft Teams webhook
│   └── utils.py                 # Utilities (timezone, mappings, formatting)
├── tests/
│   └── mock_data.json           # Sample CRM data for testing
├── doc/                         # Documentation files
├── host.json                    # Azure Functions host configuration
├── local.settings.json          # Local environment variables (create from template)
├── local.settings.template.json # Template for local settings
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Prerequisites

- **Python 3.11** or higher
- **Azure Functions Core Tools** v4.x
- **API Keys**:
  - Brevo API key (from Brevo account settings)
  - OpenAI API key (from OpenAI platform)
  - Microsoft Teams webhook URL

## Local Development Setup

### 1. Navigate to Project Directory

```bash
cd CRM-Automation
```

### 2. Install Python 3.11 (if needed)

**Check your Python version**:
```bash
python3 --version
```

**If you have Python 3.9 or lower, install Python 3.11**:

**macOS** (using Homebrew):
```bash
brew install python@3.11
```

**Windows**:
Download from [python.org](https://www.python.org/downloads/)

### 3. Create Virtual Environment

```bash
# Use python3.11 if you just installed it
python3.11 -m venv venv

# Or use python3 if you already have 3.11+
python3 -m venv venv

# Activate the environment
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Copy the template file and rename it:

```bash
cp local.settings.template.json local.settings.json
```

Then edit `local.settings.json` with your actual API keys:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "BREVO_API_KEY": "your-actual-brevo-api-key",
    "OPENAI_API_KEY": "your-actual-openai-api-key",
    "TEAMS_WEBHOOK_URL": "your-actual-teams-webhook-url",
    "USE_MOCK_DATA": "false"
  }
}
```

**Important**:
- Set `USE_MOCK_DATA=true` to test with sample mock data (no API keys needed for Brevo)
- Set `USE_MOCK_DATA=false` to use real Brevo data
- `local.settings.json` is in `.gitignore` - your API keys won't be pushed to GitHub
- `TEAMS_WEBHOOK_URL` is not used when running `test_local.py`

### 6. Install Azure Functions Core Tools

**macOS** (using Homebrew):
```bash
brew tap azure/functions
brew install azure-functions-core-tools@4
```

**Windows** (using npm):
```bash
npm install -g azure-functions-core-tools@4
```

**Linux**:
```bash
# Follow instructions at: https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local
```

## Testing Locally

### Quick Test (Recommended)

Use `test_local.py` to test the full flow without sending to Teams:

```bash
# Activate virtual environment
source venv/bin/activate

# Run the test
python test_local.py
```

This script:
- Fetches data from Brevo (real or mock depending on `USE_MOCK_DATA`)
- Generates the AI summary
- Displays everything in the console (does NOT send to Teams)

**Customize the test**: Edit line 37 in `test_local.py` to change `DAYS_BACK`:
```python
DAYS_BACK = 3  # Number of days to look back for data
```

**Note**: In production, the system uses 24 hours (or 72 hours on Mondays). For testing, you can set any number of days.

### Test with Azure Functions Runtime

1. Ensure your settings are configured in `local.settings.json`
2. Start the function locally:

```bash
func start
```

3. Trigger the function manually:

```bash
# In a new terminal window
curl -X POST http://localhost:7071/admin/functions/DailyReportFunction -H "Content-Type: application/json" -d "{}"
```

**Warning**: This will send the report to Teams if you have a real webhook URL configured.

**Note**: When testing with real APIs, be mindful of API rate limits and costs (especially OpenAI).

## Schedule Configuration

The function runs **Monday-Friday at 7:00 AM Toronto time**.

### Timer Trigger

Located in [DailyReportFunction/function.json](DailyReportFunction/function.json):

```json
{
  "schedule": "0 0 12 * * 1-5"
}
```

**CRON Expression**: `0 0 12 * * 1-5`
- `0` - Second (0)
- `0` - Minute (0)
- `12` - Hour (12:00 PM UTC = 7:00 AM EST in winter)
- `*` - Day of month (any)
- `*` - Month (any)
- `1-5` - Day of week (Monday-Friday)

**Important**: Azure Functions uses UTC time. The schedule `12:00 PM UTC` corresponds to:
- **7:00 AM EST** (winter - standard time)
- **8:00 AM EDT** (summer - daylight saving time)

For year-round 7:00 AM Toronto time, you may need to adjust the schedule seasonally or use a more sophisticated scheduling approach.

### Lookback Period Logic

Implemented in [shared/utils.py](shared/utils.py):

- **Monday**: 72-hour lookback (includes Friday + weekend)
- **Tuesday-Friday**: 24-hour lookback

## Data Extraction

### Brevo API Endpoints

**Notes**: `GET /v3/crm/notes`
- Extracts: text, author, companyIds, createdAt
- Filtering applied:
  - Company-level notes only (must have companyIds, excludes contactIds and dealIds)
  - Excludes notes ending with "Generated automatically by Aura"
- Enriched with company details

**Companies**: `GET /v3/companies/{id}`
- Extracts: name, distributor, business_division_2, industry

**Deals**: `GET /v3/crm/deals`
- Extracts: deal_name, deal_owner, deal_stage, pipeline_id, distributor, amount, opportunity_type, timestamps
- Differentiation logic:
  - New deals: created_at within reporting period
  - Updated deals: stage_updated_at within reporting period but created_at before period

### Pipeline Mappings

The system supports multiple sales pipelines with configurable stages. Pipeline IDs and stage IDs are mapped to human-readable names in the codebase.

### User Mappings

User IDs from the CRM are mapped to display names for report generation. The mapping is easily expandable to accommodate additional users as the team grows.

## Report Generation

### OpenAI GPT Summary

The AI generates an executive summary with:
- Title format: `[Day of Week], [Month] [Day], [Year] – CRM Executive Summary`
- Organized by owner (sales representative)
- Thematic categorization of activities
- Action-oriented bullet points
- Separate sections for new deals and updated deals
- Clickable company and deal links
- Professional formatting suitable for executive review

### Report Format

Reports are sent to Microsoft Teams with markdown formatting (clickable links supported):
- Hyperlinked company names → `https://app.brevo.com/companies/detail/{id}`
- Hyperlinked deal names → `https://app.brevo.com/crm/deals/detail/{id}`
- Professional formatting suitable for executives

## Error Handling

The function implements graceful error handling:

1. **Partial Data Failures**: If notes API fails but deals succeed (or vice versa), generates report with available data and includes error notice
2. **Complete API Failures**: Sends error summary to Teams with details
3. **OpenAI Failures**: Creates manual error report and sends to Teams
4. **Teams Webhook Failures**: Logs errors but doesn't crash the function

All errors are logged to Azure Application Insights for monitoring.

## Deployment to Azure

### Prerequisites

- Azure subscription
- Azure Resource Group
- Azure Function App (Python 3.11, Linux)
- Azure Key Vault (for production secrets)

### Deployment Steps

1. **Install Azure CLI**:
```bash
# macOS
brew install azure-cli

# Windows
# Download from: https://aka.ms/installazurecliwindows
```

2. **Login to Azure**:
```bash
az login
```

3. **Deploy Function App**:
```bash
# Replace with your function app name
func azure functionapp publish <YOUR_FUNCTION_APP_NAME>
```

4. **Configure Application Settings** (via Azure Portal or CLI):
```bash
az functionapp config appsettings set \
  --name <YOUR_FUNCTION_APP_NAME> \
  --resource-group <YOUR_RESOURCE_GROUP> \
  --settings \
    "BREVO_API_KEY=@Microsoft.KeyVault(SecretUri=https://<vault>.vault.azure.net/secrets/brevo-api-key/)" \
    "OPENAI_API_KEY=@Microsoft.KeyVault(SecretUri=https://<vault>.vault.azure.net/secrets/openai-api-key/)" \
    "TEAMS_WEBHOOK_URL=@Microsoft.KeyVault(SecretUri=https://<vault>.vault.azure.net/secrets/teams-webhook-url/)" \
    "USE_MOCK_DATA=false"
```

### Using Azure Key Vault

For production, store secrets in Azure Key Vault:

1. **Create secrets**:
```bash
az keyvault secret set --vault-name <YOUR_VAULT_NAME> --name "brevo-api-key" --value "YOUR_KEY"
az keyvault secret set --vault-name <YOUR_VAULT_NAME> --name "openai-api-key" --value "YOUR_KEY"
az keyvault secret set --vault-name <YOUR_VAULT_NAME> --name "teams-webhook-url" --value "YOUR_URL"
```

2. **Grant Function App access**:
```bash
az functionapp identity assign --name <YOUR_FUNCTION_APP_NAME> --resource-group <YOUR_RESOURCE_GROUP>

# Note the principalId from output, then:
az keyvault set-policy \
  --name <YOUR_VAULT_NAME> \
  --object-id <PRINCIPAL_ID> \
  --secret-permissions get list
```

## Monitoring

### View Logs

**Local**:
```bash
# Logs appear in terminal when running func start
```

**Azure Portal**:
1. Navigate to Function App → Functions → DailyReportFunction
2. Click "Monitor" → "Logs"
3. Or use Application Insights for advanced queries

**Azure CLI**:
```bash
# Stream live logs
func azure functionapp logstream <YOUR_FUNCTION_APP_NAME>
```

### Key Metrics to Monitor

- Function execution success rate
- API response times (Brevo, OpenAI, Teams)
- Error rates and types
- OpenAI token usage
- Function execution duration

## Customization

### Modify Report Title Format

Edit [shared/utils.py](shared/utils.py):

```python
def format_report_title() -> str:
    report_date = get_report_date()
    return f"{report_date.strftime('YOUR FORMAT HERE')}"
```

### Adjust OpenAI Prompt

Edit [shared/openai_client.py](shared/openai_client.py) (lines 187-216):

```python
def _build_system_prompt(self) -> str:
    return """Your custom prompt here..."""
```

### Change OpenAI Model

Edit [shared/openai_client.py](shared/openai_client.py) (line 26):

```python
def __init__(self, api_key: Optional[str] = None, model: str = "gpt-5"):
```

Available models: `gpt-5`, `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`

### Change Schedule

Edit [DailyReportFunction/function.json](DailyReportFunction/function.json):

```json
{
  "schedule": "0 0 12 * * 1-5"  // Modify CRON expression
}
```

CRON format: `{second} {minute} {hour} {day} {month} {day-of-week}`

### Add More Pipelines or Users

Edit [shared/utils.py](shared/utils.py):

```python
PIPELINE_MAPPINGS = {
    "your-pipeline-id": {
        "name": "Pipeline Name",
        "stages": {
            "stage-id": "Stage Name"
        }
    }
}

USER_MAPPINGS = {
    "user-id": "User Name"
}
```