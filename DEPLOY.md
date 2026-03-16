# Deployment Checklist

## Railway Environment Variables Required

### Core credentials
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY
- GEMINI_API_KEY
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- POSTHOG_API_KEY
- POSTHOG_HOST
- LINEAR_API_KEY
- LINEAR_TEAM_ID

### Gmail search config
- GMAIL_EVENTS_SEARCH_DAYS=28

### OAuth tokens (base64 encoded)
- GMAIL_READ_TOKEN_B64
- GMAIL_SEND_TOKEN_B64
- CALENDAR_TOKEN_B64

### Production settings
- SEND_MODE=true
- LUMA_CALENDAR_ID=cal-Qc8mENGhp17oisF

## Generating base64 tokens locally

Run this command in the project root:

```bash
python3 -c "
import base64
for name, file in [
    ('GMAIL_READ_TOKEN_B64', 'gmail_read_token.json'),
    ('GMAIL_SEND_TOKEN_B64', 'gmail_send_token.json'),
    ('CALENDAR_TOKEN_B64', 'calendar_token.json'),
]:
    with open(file) as f:
        encoded = base64.b64encode(f.read().encode()).decode()
    print(f'{name}={encoded}')
    print()
"
```

Copy each value to Railway environment variables.

## Re-deployment after token refresh

If OAuth tokens expire:
1. Delete local token files
2. Run OAuth flows locally
3. Regenerate base64 values
4. Update Railway environment variables
5. Redeploy
