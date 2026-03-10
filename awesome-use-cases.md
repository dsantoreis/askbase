# Awesome Use Cases

Real-world scenarios where Askbase cuts support resolution time from hours to seconds.

## 1. SaaS Customer Support

**Problem:** Support agents search 15+ docs to answer billing questions.
**Solution:** Ingest billing docs, FAQs, and policy PDFs into Askbase. Agents ask in natural language.
**Result:** Average resolution time drops from 12 minutes to 45 seconds. Every answer includes the source paragraph.

```python
response = client.ask("Can a customer downgrade mid-cycle?", top_k=3)
# Returns answer + exact doc citations
```

## 2. Developer Onboarding

**Problem:** New engineers spend 2 weeks reading internal wikis before they can answer questions.
**Solution:** Index the wiki, runbooks, and architecture docs.
**Result:** Day-one accuracy for new hires. No more "ask Sarah, she knows."

## 3. Compliance Audits

**Problem:** Auditors request evidence across scattered policy documents.
**Solution:** Ingest compliance policies (SOC2, GDPR, HIPAA). Query by control ID or keyword.
**Result:** Audit prep goes from 3 days to 2 hours. Every response cites document name, section, and character offsets.

## 4. IT Helpdesk Triage

**Problem:** L1 agents escalate 60% of tickets because they can't find the right KB article.
**Solution:** Askbase surfaces the relevant KB article with confidence scores.
**Result:** Escalation rate drops to 25%. L1 resolves more tickets without handoff.

## 5. Legal Contract Review

**Problem:** Lawyers manually search contract templates for specific clauses.
**Solution:** Index contract library. Query: "Which contracts have non-compete clauses longer than 2 years?"
**Result:** Contract review for clause patterns takes minutes instead of days.

## 6. Product Documentation Bot

**Problem:** Users ask the same questions in support channels. Docs exist but nobody reads them.
**Solution:** Embed Askbase as a chatbot on the docs site. Users get instant answers with links to the relevant page.
**Result:** Support ticket volume drops 35%. Users self-serve.

## 7. Internal Knowledge Base for Sales

**Problem:** Sales reps can't find competitive positioning or pricing details during calls.
**Solution:** Ingest battlecards, pricing sheets, and case studies.
**Result:** Reps get real-time answers during prospect calls. Win rate improves.

## 8. Healthcare Patient FAQ

**Problem:** Clinic staff answers the same insurance and procedure questions 50 times per day.
**Solution:** Ingest patient handouts, insurance guides, and procedure docs.
**Result:** Staff handles 3x more patients. Answers are consistent and cited.

## 9. E-commerce Returns Policy

**Problem:** Customer service agents give inconsistent answers about return windows and exceptions.
**Solution:** Single source of truth: ingest the returns policy and its edge cases.
**Result:** Every agent gives the same answer. Disputes drop.

## 10. Academic Research Assistant

**Problem:** Researchers search across hundreds of papers to find relevant methodology sections.
**Solution:** Ingest paper PDFs. Query by method, dataset, or finding.
**Result:** Literature review that took weeks now takes hours. Every result cites the paper and section.
