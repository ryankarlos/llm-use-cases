# NHS Patient Booking Demo

AI-powered patient booking using Amazon Bedrock Agents with web search for NHS.uk.

## Features

- Book GP/specialist appointments via text or voice
- Real-time agent status updates
- Web search for NHS.uk info (no Knowledge Base needed)
- Email/SMS confirmations (simulated)

## Quick Start

```bash
# 1. Deploy
cd terraform && terraform init && terraform apply -auto-approve

# 2. Set env vars
eval "$(terraform output -raw env_vars)"

# 3. Run app
cd ../app && pip install -r ../requirements.txt && streamlit run streamlit_app.py
```

## Tests

```bash
pytest tests/ -v
```

## Cleanup

```bash
cd terraform && terraform destroy -auto-approve
```

## Notes

- Demo only, not for production
- No medical advice - only bookings
- Bedrock usage incurs costs
