# ZubiLook Privacy Policy - canonical EN working draft

> Created: 10.07.2026 | 14:10 | Bali  
> Status: DRAFT - DO NOT PUBLISH WITH PLACEHOLDERS  
> Version: `{{POLICY_VERSION}}` | Effective date: `{{EFFECTIVE_DATE}}`

This English source draft must be translated into Russian and Uzbek only after the
operator details, production processors, and storage regions are confirmed.

## 1. Who operates ZubiLook

The personal-data operator is `{{OPERATOR_NAME}}`, registered in
`{{OPERATOR_COUNTRY}}`, address: `{{OPERATOR_ADDRESS}}` (the "Operator", "we").

Privacy requests: `{{PRIVACY_EMAIL}}`.

## 2. Scope

This Policy applies to `zubilook.com`, ZubiLook beta applications, early-access forms,
clinic-partner applications, smile visualizations, and the user-selected clinic lead
flow. ZubiLook produces an AI visualization, not a diagnosis, treatment plan, medical
recommendation, or guaranteed clinical result.

## 3. Data we process

For early access we may process name, phone or email, city, user/clinic interest,
comment, locale, consent record, and submission time.

For clinic applications we may process clinic name, city, representative name and role,
phone, email, lead volume, partnership interest, message, locale, consent record, and
submission time.

During the future closed beta we may also process phone-based account identifiers,
selfies, generated visualizations, selected smile style, generation metadata, city,
selected clinic, consultation request data, payment records, security logs, and technical
diagnostics. We do not ask users to submit medical records through the website forms.

A face image is sensitive personal content and may be treated as biometric data where it
is processed for identification or where applicable law classifies the processing that
way. ZubiLook must not use a face image to identify a person without a separate lawful
basis and disclosure.

## 4. Why we process data

We process data to:

- respond to early-access and clinic-partner requests;
- provide and improve the requested smile visualization;
- authenticate the user and protect the service;
- show the user's history and generation balance;
- send a consultation request only to the clinic selected by the user;
- provide support and handle privacy requests;
- meet legal, accounting, security, and dispute-resolution obligations.

The applicable basis is the user's consent, steps requested by the user before entering
an agreement, performance of an agreement, the Operator's legitimate interests where
permitted, or a legal obligation. The concrete basis must be stated per processing
purpose in the final jurisdiction-specific version.

## 5. Service providers and recipients

Production providers may include Supabase for database, authentication, and storage;
Vercel for the public website; Railway for the backend; Fal.ai for the requested image
generation; email or WhatsApp providers for notifications; payment providers for paid
features; and Sentry or Mixpanel only after those services are enabled.

The final Policy will list only providers actually enabled in production, their purpose,
and relevant processing region. A clinic receives the user's contact details and
visualization only after the user selects that clinic and submits the consultation
request. One lead is sent to one selected clinic; ZubiLook does not resell the same lead
to multiple clinics.

## 6. International processing

Some providers may process data outside the user's country. The final Policy will name
the relevant countries or safeguards after `{{SUPABASE_REGION}}`, Railway, Fal.ai, and
other production regions are confirmed.

ZubiLook will not launch photo processing for users in Uzbekistan until the Operator has
confirmed whether the processing is biometric under local law and has satisfied any
applicable local-storage, registration, and cross-border requirements.

## 7. Retention

- Early-access and clinic application data: up to 12 months after submission, or until
  the request is resolved or consent is withdrawn, unless a longer legal period applies.
- Original selfies and generated visualizations: up to 30 days, then hard-deleted from
  active storage. This statement becomes effective only after the automated deletion job
  is deployed and verified.
- Account data: while the account is active and for the limited period required to
  complete deletion, prevent fraud, or meet legal obligations.
- Consent, transaction, and dispute records: for the period required by applicable law.

We may retain anonymized statistics that no longer identify a person.

## 8. Security

We use access controls, private storage, signed time-limited URLs, server-side inference
credentials, least-privilege database policies, encryption in transit, logging, and
retention controls appropriate to the beta stage. No online service can guarantee
absolute security.

## 9. User choices and rights

Depending on applicable law, a user may ask whether we process their data, request a
copy, correction, restriction, deletion, or withdrawal of consent, and complain to the
competent authority. Withdrawing consent does not affect processing completed before
the withdrawal.

Send requests to `{{PRIVACY_EMAIL}}`. We may ask for proportionate verification before
acting on a request. The final Policy will state jurisdiction-specific response periods.

## 10. Age limit

The closed beta is intended only for people aged 18 or older. We do not knowingly
collect a minor's selfie or account data. If we learn that such data was submitted, we
will block processing and delete it unless a valid guardian process is implemented.

## 11. Changes

We will publish the current version and effective date on the website. Material changes
that affect existing consent will require renewed notice or consent where applicable.

## 12. Contact

Operator: `{{OPERATOR_NAME}}`  
Address: `{{OPERATOR_ADDRESS}}`  
Email: `{{PRIVACY_EMAIL}}`
