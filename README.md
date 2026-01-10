# Brevo CRM Daily Automation

Automated daily reporting system that extracts CRM activity from Brevo, generates AI-powered executive summaries using OpenAI GPT-4, and delivers formatted reports to Microsoft Teams.

## Features

- **Automated Data Extraction**: Pulls last 24 hours of CRM activity from Brevo API (72 hours on Mondays)
- **AI-Powered Summaries**: Generates executive-level summaries using OpenAI GPT-4
- **Teams Integration**: Delivers formatted reports via Microsoft Teams webhook
- **Timezone-Aware**: Handles Toronto (EST/EDT) to UTC conversions automatically
- **Mock Data Support**: Test locally without hitting real APIs
- **Error Resilience**: Sends partial reports with error notices when APIs fail
- **Production-Ready**: Comprehensive logging and error handling

## Project Structure

```
brevo-crm-automation/
├── DailyReportFunction/
│   ├── __init__.py              # Main Azure Function handler
│   └── function.json            # Timer trigger configuration
├── shared/
│   ├── brevo_client.py          # Brevo API integration
│   ├── openai_client.py         # OpenAI GPT-4 integration
│   ├── teams_client.py          # Microsoft Teams webhook
│   └── utils.py                 # Utilities (timezone, mappings, formatting)
├── tests/
│   └── mock_data.json           # Sample CRM data for testing
├── host.json                    # Azure Functions host configuration
├── local.settings.json          # Local environment variables
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

### 1. Clone and Navigate to Project

```bash
cd /Users/nataliacuellas/Desktop/Programming/CRM-Automation
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Edit [local.settings.json](local.settings.json):

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "BREVO_API_KEY": "your-actual-brevo-api-key",
    "OPENAI_API_KEY": "your-actual-openai-api-key",
    "TEAMS_WEBHOOK_URL": "your-actual-teams-webhook-url",
    "USE_MOCK_DATA": "true"
  }
}
```

**Important**:
- Set `USE_MOCK_DATA=true` to test with mock data
- Set `USE_MOCK_DATA=false` to use real APIs
- Never commit `local.settings.json` with real API keys

### 5. Install Azure Functions Core Tools

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

### Test with Mock Data

1. Ensure `USE_MOCK_DATA=true` in [local.settings.json](local.settings.json)
2. Start the function locally:

```bash
func start
```

3. Trigger the function manually:

```bash
# In a new terminal window
curl -X POST http://localhost:7071/admin/functions/DailyReportFunction -H "Content-Type: application/json" -d "{}"
```

### Test with Real APIs

1. Update [local.settings.json](local.settings.json) with real API keys
2. Set `USE_MOCK_DATA=false`
3. Start and trigger the function as above

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
- Enriched with company details

**Companies**: `GET /v3/crm/companies/{id}`
- Extracts: name, distributor, business_division, industry

**Deals**: `GET /v3/crm/deals`
- Extracts: deal_name, deal_owner, deal_stage, pipeline_id, distributor, amount, opportunity_type, timestamps

### Pipeline Mappings

**PACA Sales Pipeline** (`69580298dc36c3319adb3093`):
- Identified
- Qualifying + Assessment
- Proposal Sent
- In negotiation
- On-Hold
- Won
- Lost

**WHD Sales Pipeline** (`6849de42a68e1c112aa30e83`):
- Identified
- Qualifying + Assessment
- Proposal Sent to rep
- In negotiation
- On-Hold
- Won
- Lost

### User Mappings

- `6849de2c8da98f55690819b3` = Nicolas Attieh
- `6866dcf3af9c593d0806bb57` = Marvin Escalante

## Report Generation

### OpenAI GPT-4 Summary

The AI generates an executive summary with:
- Title format: `[Day of Week], [Month] [Day], [Year] – CRM Executive Summary`
- Organized by Owner (sales rep)
- Thematic categorization of activities
- Action-oriented bullet points
- New deals and deal updates sections
- Clickable company and deal links

### Report Format

Reports are sent as Microsoft Teams Adaptive Cards with markdown formatting:
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

Edit [shared/openai_client.py](shared/openai_client.py):

```python
def _build_system_prompt(self) -> str:
    return """Your custom prompt here..."""
```

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

## Troubleshooting

### Function Not Triggering

1. Check timer trigger configuration in [function.json](DailyReportFunction/function.json)
2. Verify Function App is running (Azure Portal)
3. Check timezone conversion in [utils.py](shared/utils.py)

### API Connection Errors

1. Verify API keys in [local.settings.json](local.settings.json) or Azure settings
2. Check network connectivity
3. Verify Brevo API endpoint URLs
4. Review API rate limits

### OpenAI Errors

1. Check API key validity
2. Verify model name (currently "gpt-4")
3. Monitor token usage (max 4000 tokens)
4. Check OpenAI account credits/billing

### Teams Webhook Not Receiving

1. Verify webhook URL is correct
2. Test webhook with simple message:
```bash
curl -X POST YOUR_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{"text": "Test message"}'
```
3. Check Teams channel permissions

### Mock Data Not Loading

1. Verify [tests/mock_data.json](tests/mock_data.json) exists
2. Check JSON syntax is valid
3. Ensure `USE_MOCK_DATA=true` in settings

## Development Notes

### Adding New Features

1. Create feature branch
2. Update relevant modules in [shared/](shared/)
3. Update [mock_data.json](tests/mock_data.json) if needed
4. Test locally with mock data
5. Test with real APIs (carefully)
6. Update this README

### Code Style

- Follow PEP 8 conventions
- Use type hints
- Include docstrings for all functions
- Add comprehensive error handling
- Log important steps at INFO level

### Testing Checklist

- [ ] Test with mock data
- [ ] Test with real Brevo API
- [ ] Test with real OpenAI API
- [ ] Test Teams webhook delivery
- [ ] Test Monday (72-hour lookback)
- [ ] Test Tuesday-Friday (24-hour lookback)
- [ ] Test error scenarios (API failures)
- [ ] Test empty data scenarios
- [ ] Verify timezone conversions
- [ ] Check hyperlinks in report

## Cost Considerations

### OpenAI API
- GPT-4 costs approximately $0.03 per 1K prompt tokens and $0.06 per 1K completion tokens
- Estimated cost per report: $0.20-$0.50 (varies by data volume)
- Monthly cost (20 business days): $4-$10

### Brevo API
- Check your Brevo plan for API call limits
- Function makes: ~1 notes request + N company requests + ~1 deals request
- Stay within your plan's limits

### Azure Functions
- Consumption plan typically $0-$10/month for this workload
- Monitor execution time and memory usage

## Security Best Practices

1. **Never commit secrets**: Use `.gitignore` for `local.settings.json`
2. **Use Key Vault in production**: Store all secrets in Azure Key Vault
3. **Restrict webhook access**: Secure Teams webhook URL
4. **Monitor API usage**: Watch for unusual activity
5. **Rotate keys regularly**: Update API keys periodically
6. **Limit permissions**: Use minimal required permissions for Azure resources

## Support and Maintenance

### Logs to Review

- Azure Function execution logs
- Application Insights telemetry
- Teams message delivery confirmation
- API rate limit warnings

### Regular Maintenance

- [ ] Monitor OpenAI token usage trends
- [ ] Review error logs weekly
- [ ] Update dependencies monthly
- [ ] Rotate API keys quarterly
- [ ] Test mock data accuracy

## License

Proprietary - Internal Use Only

## Contact

For questions or issues, contact the development team.

---

**Last Updated**: January 2026
**Version**: 1.0.0
# crm-automation
