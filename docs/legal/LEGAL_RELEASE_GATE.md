# ZubiLook legal release gate

> Created: 10.07.2026 | 14:10 | Bali  
> Status: BLOCKED until the operator details and infrastructure facts below are confirmed.

This checklist is an internal release control, not legal advice. The public documents
must be reviewed for the operator's actual jurisdiction before real-user beta access.

## Official-source baseline

- Russia: Federal Law No. 152-FZ "On Personal Data" requires a public personal-data
  policy and disclosures about the operator, purposes, data categories, processing,
  retention, recipients, subject rights, and cross-border transfers. Roskomnadzor also
  states that a website collecting identifiable contact data is a personal-data operator
  and may need to notify the regulator before processing begins.
- Uzbekistan: Law No. O'RQ-547 "On Personal Data", as amended effective 27.03.2026,
  covers consent and withdrawal, subject access, security, confidentiality, retention,
  operator duties, cross-border processing, and special storage rules. Article 27-1
  requires biometric and genetic data listed there to be stored in Uzbekistan.

Primary sources:

- https://ips.pravo.gov.ru/api/ips/legislation/document?baseid=None&hash=98490812b3409e2a8d78a11ca9010f434ea3d9250a11dbbdb78690cd5551bdd6
- https://82.rkn.gov.ru/directions/pers/p15375/
- https://lex.uz/ru/docs/-4396419

## Information Selena must confirm

1. Operator's full legal name or full individual name.
2. Registration country and legal/postal address.
3. Privacy contact email. Proposed default: `parkourcafe@gmail.com`.
4. Whether the beta is restricted to users aged 18+. Proposed default: yes.
5. Supabase project region and the regions used by Railway, Fal.ai, email, analytics,
   and error monitoring.
6. Initial beta geography: Russia only, Uzbekistan only, or both.
7. Whether the operator has completed any required personal-data regulator notice or
   database registration in the launch jurisdictions.

## Technical release requirements

- [ ] Landing forms use Supabase only after migration `0008_waitlist.sql` is applied.
- [ ] Consent is unchecked by default and links to the published Privacy Policy.
- [ ] Consent timestamp, policy version, form source, and locale are stored.
- [ ] App photo upload requires separate explicit consent before the first upload.
- [ ] User can withdraw consent and request access, correction, export, or deletion.
- [ ] Original and generated photos are hard-deleted after 30 days.
- [ ] A selected clinic receives data only after a separate user action.
- [ ] Processor and cross-border transfer list reflects production, not planned services.
- [ ] Uzbekistan photo processing is not launched until biometric classification and
      Article 27-1 hosting requirements are confirmed by local counsel.
- [ ] Privacy and Terms pages are available in RU, EN, and UZ from every form and app.
- [ ] Legal review records the approved document versions and effective date.

## Publication decision

Do not label ZubiLook "152-FZ compliant" or "fully compliant" based only on these
documents. Publication can proceed when all operator placeholders are resolved and the
technical behavior matches the text. Real-user photo beta requires the retention job,
data-subject request flow, and jurisdiction-specific hosting decision.

