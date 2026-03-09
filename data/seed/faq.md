# Askbase Platform — Frequently Asked Questions

## Account & Access

**How do I reset my password?**
Go to Settings > Security > Reset Password. You will receive a confirmation email within 2 minutes. If you do not receive it, check your spam folder or contact support@askbase.io. Password reset links expire after 24 hours.

**What are the different user roles?**
Askbase has three roles: Viewer (read-only access to dashboards), Editor (can create and modify content), and Admin (full access including billing, user management, and API keys). Role changes take effect immediately.

**How do I enable two-factor authentication (2FA)?**
Navigate to Settings > Security > Two-Factor Authentication. You can use any TOTP-compatible app (Google Authenticator, Authy, 1Password). Scan the QR code and enter the 6-digit verification code. Backup codes are generated automatically — store them securely.

**Can I invite team members?**
Yes. Go to Settings > Team > Invite Member. Enter their email address and select a role. They will receive an invitation valid for 7 days. You can resend or revoke invitations from the same page.

## Billing & Plans

**What plans are available?**
We offer three plans: Starter ($29/month, up to 5 users, 10k queries/month), Professional ($99/month, up to 25 users, 100k queries/month), and Enterprise (custom pricing, unlimited users and queries, SSO, dedicated support). All plans include a 14-day free trial.

**How do I upgrade or downgrade my plan?**
Go to Settings > Billing > Change Plan. Upgrades take effect immediately and are prorated. Downgrades take effect at the end of the current billing cycle.

**What payment methods do you accept?**
We accept Visa, Mastercard, American Express, and invoiced billing for Enterprise plans. All payments are processed securely through Stripe.

**Is there a refund policy?**
Yes. We offer a full refund within 30 days of your first payment. After that, you can cancel anytime and retain access until the end of your billing period.

## Data & Privacy

**Where is my data stored?**
All data is stored in AWS US-East-1 by default. Enterprise customers can choose from US-East-1, EU-West-1, or AP-Southeast-1 regions. Data is encrypted at rest (AES-256) and in transit (TLS 1.3).

**Can I export my data?**
Yes. Go to Settings > Data > Export. You can export all documents, queries, and analytics in JSON or CSV format. Exports are available within 1 hour for accounts with up to 100k documents.

**What is your data retention policy?**
Query logs are retained for 90 days by default. Documents are retained until manually deleted. Enterprise customers can configure custom retention periods from 30 days to indefinite.

**Are you SOC 2 compliant?**
Yes. Askbase is SOC 2 Type II certified. Our latest audit report is available upon request for Enterprise customers. Contact security@askbase.io.

## Integrations

**Does Askbase integrate with Slack?**
Yes. Install the Askbase Slack app from our integrations page. Once connected, users can query the knowledge base directly from any Slack channel using the `/askbase` command. Answers include citations and source links.

**Does Askbase integrate with Microsoft Teams?**
Yes. The Askbase Teams bot can be added to any channel. Users mention @Askbase followed by their question. Responses are threaded and include citation links to source documents.

**Can I use the REST API?**
Yes. All features are available via REST API. Authenticate with a Bearer token and use endpoints like POST /ask, POST /ingest, and GET /admin/stats. Full API documentation is available at docs.askbase.io/api.

**Is there a webhook for new answers?**
Yes. Configure webhooks under Settings > Integrations > Webhooks. You can receive POST notifications when new answers are generated, documents are ingested, or evaluation scores change.
