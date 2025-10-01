## Setup Prerequisites

- Python 3.8+
- Jenkins instance with API access
- Google Gemini API key
- Slack workspace with admin access

## Steps

1. Install dependencies
2. Configure .env file
3. Run the app
4. Expose locally using ngrok (for development)
5. Create Slack App at api.slack.com/apps
   - Subscribe to `app_mention` event
   - Set Request URL to your endpoint `/slack/events`
6. Test in Slack!
