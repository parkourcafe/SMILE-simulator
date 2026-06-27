> Auto-extracted plain text from the source `.docx` for readable reference. The `.docx` remains the canonical version.


AI Smile Simulator
Partner Brief & MVP Plan
Version 2.4 — 28.06.2026 — Bali
Target markets: Russia & Uzbekistan

Document status: preliminary partner brief. All timelines and amounts are working estimates. Before investment decision, confirm current API/inference rates, payment commissions, legal requirements for photo processing, and quality test results on real selfies.

Key Conclusion
Decision
Recommended start
Option 2: Inpainting + Flux. Best balance of speed, quality, and cost for paid MVP.
What NOT to do
Do not start with custom LoRA until demand, quality, and generation economics are verified.
First checkpoint
Prototype + test on 20–30 real selfies + cost per successful generation.
Primary revenue driver
B2B (dental clinics): per-lead + embeddable widget. B2C = awareness funnel.
Target geography
Russia (Moscow + SPb first) + Uzbekistan (Tashkent). Early-stage market with emerging local competitors (SmileVision). No dominant B2C → B2B lead-gen platform yet.

1. Executive Summary
AI Smile Simulator is a mobile app that allows users to upload a selfie and receive a visualization of a new smile: straighter, whiter, and more aesthetically pleasing teeth. The product should be perceived as visual simulation, not dental diagnosis or treatment guarantee.
Recommended path: MVP launch on Option 2 — inpainting of the mouth area only. Revenue model: B2B per-lead for dental clinics (primary) with B2C consumer app as the acquisition funnel (secondary). Target markets: Russia and Uzbekistan — early-stage markets where no dominant B2C → B2B lead-generation platform exists yet, though local B2B tools (SmileVision) are already emerging.
Global benchmarks suggest that the strongest monetization patterns are clinic-paid models: SaaS, white-label widgets, per-lead flows, or bundled platforms. B2C packages should be treated as funnel monetization, not the core business model.

2. Selected Global and Local Benchmarks
The following analysis covers the most relevant competitors globally and locally. Direct and adjacent competitors already exist in Russia, but the B2C → B2B lead-generation category is not yet dominated by any single platform.

2.1. SmileViz (USA) — “Chairside Converter”
What it does: AI smile simulation in ~90 seconds. Dentist shows the patient their future smile during consultation. Pure B2B product — no consumer-facing app.
Parameter
Details
Model
B2B SaaS subscription
Pricing
Core: $299/mo, 30 preview credits. Pro: $399/mo, 100 preview credits. Top-ups: $39–59 per pack. No contracts.
Claimed ROI
3x case acceptance increase. $20K–$100K additional clinic revenue in first 90 days.
Key feature
Real-time chairside simulation. Speed is the product — generate while patient is in the chair.
Weakness for us
US-only, HIPAA-focused, $299/mo too expensive for Russian market.

Lesson: SmileViz sells speed + ROI, not technology. One additional veneer case ($5,000–$30,000) pays for 12–18 months of subscription. This ROI argument works in Russia too.

2.2. Simmetry by ToothLens (USA) — “24/7 Lead Machine”
What it does: AI smile simulation + embeddable widget for clinic websites. Captures leads after-hours when the clinic is closed. 30% of dental inquiries happen at night.
Parameter
Details
Model
B2B SaaS + lead generation widget
Pricing
Not public (demo-based sales). Enterprise approach.
Claimed results
98% patient satisfaction, 40% reduction in chair time, 35% increase in patient retention.
Key feature
24/7 widget on clinic website. Patient uploads selfie at 2 AM, sees result, leaves contact. Clinic gets warm lead in the morning.
Weakness for us
No Russian language, no CIS presence. Demo-based sales = heavy sales process.

Lesson: The widget model is the most transferable to Russia. Clinics already have websites. A widget that captures leads 24/7 with zero effort from the clinic is an easy sell at per-lead pricing.

2.3. denta.bot (UK) — “White-Label Widget + Video”
What it does: Browser-based AI smile simulator. White-label for clinics — embed on website, landing pages, ad campaigns. Photo + video preview in <60 seconds.
Parameter
Details
Model
B2B white-label widget
Pricing
Not public (demo-based). Per-clinic licensing.
Key feature
AI-generated VIDEO of patient’s future smile in motion (not just static photo). Premium upsell.
Differentiator
Manufacturer-independent (not tied to Invisalign, DSD, or any brand). Works for any treatment type.
Weakness for us
UK-focused, small team, no CIS market.

Lesson: Video simulation > photo simulation for conversion. “Your future smile in motion” creates stronger emotional response than a still image. This should be a Phase 2 feature.

2.4. SmileFy (USA/Global) — “Platform + Education”
What it does: Full cycle — AI smile design + 3D CAD + 3D printing of mock-ups/temporaries. Photo to physical veneer prototype in one visit.
Parameter
Details
Model
B2B SaaS (tiered) + education academy
Pricing
Basic (2D): free. Pro (3D + printing): $900–$1,349/year. “Done for you” with designers: $3,999/year for 10 cases.
Scale
49,000+ users in 60+ countries. Weekly live training included.
Key feature
Multi-tier monetization: free 2D → paid 3D → premium “done for you”. Academy as retention tool.
Weakness for us
Much heavier product (CAD/CAM integration). Overkill for our MVP scope.

Lesson: Freemium at 2D level (free) → upsell into 3D/premium. Education component (academy, weekly training) creates stickiness. For Russia: “free webinar on AI in dentistry” could be an acquisition channel for clinics.

2.5. DentalPrice AI (USA) — “Widget Inside a Platform”
What it does: AI smile widget embedded on clinic website. Patient uploads photo → gets photo + video preview in 15 seconds → receives email from clinic with result → fills contact form → clinic gets hot lead.
Parameter
Details
Model
B2B bundled (widget included in all plans)
Pricing
Part of broader DentalPrice AI platform. Widget is a feature, not standalone product.
Key feature
Automated email to patient with video result FROM THE CLINIC’S BRAND. Patient receives branded communication, not generic app notification.
Critical detail
Setup takes 5 minutes. Minimal friction for clinic adoption.
Weakness for us
Bundled model means smile widget subsidized by other revenue. Hard to replicate as standalone.

Lesson: Branded email from clinic to patient with smile preview = conversion machine. The patient feels they are communicating with their dentist, not with an app. This increases trust and booking rate.

2.6. Local Competitor Check: Russia/CIS
Russia is NOT an empty market. At least one direct local B2B competitor already exists, plus B2C apps with Russian-language presence.

SmileVision (Russia) — Direct B2B Competitor
SmileVision (smile-vision.ru) is a Russian AI visualization tool for dentists and clinics. It generates photo and video of a patient’s future smile in ~1 minute on a smartphone. Available on iOS and Android. Claims 168+ clinics, 8,400+ AI smiles generated.
Parameter
Details
Model
B2B SaaS for dentists and clinics
Pricing
Individual: 3,000 ₽/mo. Clinic: 12,000 ₽/mo. Clinic+: 30,000 ₽/mo. Photo: 100 ₽. Video: 500 ₽.
Key claim
Average clinic with 4 doctors recovers 180,000 ₽/mo from “postponed” patients.
Strengths
Russian language, ruble payments, 152-FZ positioning, mobile app, video generation.
Weakness vs us
Pure B2B tool for dentists. No consumer-facing app. No B2C → B2B lead-generation funnel.

Teethsi | Veneers AI (Global / RU accessible)
Teethsi is a B2C mobile app (Google Play) with Russian-language description. AI veneer visualizer with style selection and instant results. In-app purchases. No B2B clinic integration.

Implication: the opportunity is not “zero competition.” The opportunity is to build a stronger funnel model: B2C mobile app → user sees future smile → user requests real treatment → partner clinic pays per warm lead. SmileVision focuses on the dentist-side tool; we build the patient acquisition engine.

2.7. Differentiation vs Local Competitors
SmileVision is a B2B visualization tool inside the clinic. We build a B2C funnel OUTSIDE the clinic that brings patients IN.
SmileVision sells to the dentist. We sell leads TO the dentist. Different buyer psychology, different sales process.
SmileVision charges 3,000–30,000 ₽/mo fixed. We start with per-lead (zero risk for clinic) → upsell to subscription.
B2C app as acquisition engine: SmileVision doesn’t have this. Users discover us on their own, not through a dentist.
Uzbekistan as second market and dental tourism angle — not covered by any competitor.
MVP must prove not just image quality, but cost-per-lead and lead-to-patient conversion.

Positioning: AI Smile Simulator is NOT another dentist-side visualization tool. It is a patient acquisition engine for clinics, powered by a consumer-facing mobile app. This is a fundamentally different category from SmileVision.

3. Monetization Models: Complete Map
Based on analysis of all global analogues, seven distinct monetization models exist for AI smile simulation. Not all are suitable for MVP — but understanding the full landscape helps plan the product roadmap.

#
Model
Who Pays
Examples
Typical Price
MVP Fit
1
B2B SaaS subscription
Clinic, monthly
SmileViz, SmileCloud
$99–299/mo
Phase 2
2
B2B per-lead
Clinic, per warm lead
Simmetry, DentalPrice AI
$10–50/lead (US); 500–2,000₽ (RU)
YES — start here
3
B2B white-label widget
Clinic, for embed on site
denta.bot, SmilePreview
$99–499/mo
Phase 2
4
B2B education + SaaS
Clinic, annual + training
SmileFy, DSD Academy
$900–4,000/year
Phase 3
5
B2B per-case
Clinic, per design
DSD Planning Center
$50–400/case
Not our model
6
B2C freemium packs
Consumer, per generation pack
No pure analogues exist
$3–12/pack
Funnel only
7
B2C → B2B funnel
Consumer free, clinic pays for lead
AI Smile Simulator (our model)
0₽ user + 500–1,500₽/lead
YES — core model

Key finding: No successful analogue lives on B2C packages alone. All five competitors monetize through dental clinics. The only question is HOW the clinic pays: subscription, per-lead, or per-case.

4. Revenue Model for Russia & Uzbekistan
4.1. Why Per-Lead Is the Right Start
Zero risk for the clinic — they pay only for results. This is the fastest way to onboard first 15 clinics.
No sales process needed — “We send you patients interested in veneers. You pay only when they come.”
SaaS subscription ($99–199/mo) requires demo, pipeline, sales calls. Per-lead requires one WhatsApp message.
Once clinic sees ROI from leads, upsell to widget (Phase 2) and SaaS (Phase 3) becomes natural.
4.2. B2B Revenue Streams (Phased)
Phase
Model
How It Works
Price (RU)
Timeline
Phase 1
Per-lead
B2C app generates leads; clinic pays per warm lead that requests consultation
500–1,500₽/lead
MVP + first 3 months
Phase 2
Widget for clinic website
Clinic embeds AI simulator on their site. 24/7 lead capture. Monthly fee.
5,000–15,000₽/mo
Month 4–8
Phase 3
SaaS subscription
Full dashboard: leads, simulations, analytics, branded results, CRM integration
10,000–25,000₽/mo
Month 9+
Phase 4
Video simulation premium
AI video of patient’s future smile in motion. Premium add-on.
Add-on 3,000–5,000₽/mo
After demand validation
4.3. B2B Unit Economics for Russian Clinic
ROI calculation for a cosmetic dentistry clinic in Moscow:
Metric
Value
Source
Average veneer case (8 teeth, E-max)
160,000–250,000₽
Russian clinic pricing 2026
Case acceptance without visualization
~50%
Industry benchmark
Case acceptance with AI visualization
70–80%+
SmileViz data (3x improvement)
Cost of 10 leads from our app
5,000–15,000₽
Our per-lead pricing
Conversion of leads to patients
20–30%
Conservative estimate
Patients from 10 leads
2–3
Calculated
Revenue from 2–3 veneer patients
320,000–750,000₽
2–3 × 160K–250K
ROI for clinic
20–50x
Revenue / lead cost

Pitch to Russian clinic: “You spend 10,000₽ on leads, you get 2–3 veneer patients worth 300,000–750,000₽. That’s 30–75x return.” This is an easy conversation.

5. B2C Pricing: Funnel Economics
5.1. Free Tier: 1 Generation with Watermark
Global benchmark: hard paywalls convert 5x better than freemium (10.7% vs 2.1%). 50% of conversions happen on Day 0. Recommendation: 1 free generation with watermark, not 3 free without watermark.
1 free generation creates the “wow moment” and immediate desire for more.
Watermark prevents saving/sharing — user must pay to get clean result.
Instant upgrade offer at peak emotion: “Remove watermark + get 5 more for 149₽.”
5.2. Paid Packs (in local currency)
Pack
User Gets
Price RU
Price UZ
Role
Free
1 generation with watermark
0
0
Hook. Show quality, create desire.
Mini
5 generations, no watermark
149₽ (~$1.5)
15,000 sum
Impulse purchase. Low entry barrier.
Main
20 generations + 3 styles
499₽ (~$5)
50,000 sum
Main pack. Enough for comparison.
Extended
50 generations + all styles + save
899₽ (~$9)
90,000 sum
Power users. Launch after COGS confirmed.

Why not $7 as in original document: in Russia $7 = ~630₽ — awkward price point. 149₽ = impulse buy (like a Telegram sticker pack). 499₽ = deliberate but low purchase. Round ruble prices convert better than dollar-pegged amounts.
5.3. B2C-to-B2B Funnel Mechanics
The consumer app is not the business — it is the top of the funnel:
User downloads app, uploads selfie, sees 1 free result with watermark.
User pays 149₽ for mini-pack (or sees ad: “Want this smile for real?”).
App shows button: “Find a clinic near you” with partner clinics listed.
User taps, fills short form (name + phone + preferred time).
Clinic receives warm lead with: user’s photo, AI simulation result, and contact info.
Clinic pays us 500–1,500₽ for this lead.

Critical: the lead is not just a phone number. It comes with the patient’s selfie and their AI smile simulation. The clinic sees what the patient wants BEFORE the call. This is 10x more valuable than a generic dental lead from Yandex.Direct.

6. Market Context: Russia & Uzbekistan
6.1. Russia
The Russian dental services market reached 1.12 trillion rubles in 2025, growing 52% over 5 years (BusinesStat 2026). 38,500 dental organizations. Cosmetic procedures (veneers, whitening, alignment) are the fastest-growing segment. Average check: ~8,000₽, but cosmetic cases are 10–30x higher.
Veneers: composites from 8,000₽/tooth, E-max ceramic from 20,000₽/tooth, luminirs from 35,000₽/tooth.
Full smile zone (8–10 teeth): 160,000–350,000₽ ($1,800–$4,000).
Moscow/SPb: highly competitive, clinics actively invest in digital tools and marketing.
AI smile simulation: local competitors exist (SmileVision, 168+ clinics). But no B2C → B2B lead-generation platform yet.
6.2. Uzbekistan
Dental tourism growing rapidly (Turkey, Uzbekistan as budget alternatives to Russia).
Private dental clinics in Tashkent actively adopt modern equipment.
Veneer prices significantly lower than Russia — higher price sensitivity for B2C packs.
Test market for CIS expansion. Low cost to validate.
6.3. TAM → SAM → SOM
Layer
Definition
Estimate
TAM
Global cosmetic dentistry market
$35.7B (2026, Mordor Intelligence)
Russia dental market
Total dental services market
1.12 trillion ₽ (~$12.4B)
SAM
Cosmetic dentistry in Russia (veneers, whitening, alignment)
$1.5–2.5B (est.)
Serviceable slice
AI smile simulation tools (B2B + B2C) in CIS
$50–150M (est.)
SOM (Year 1)
50–100 clinic partnerships + B2C funnel
$50–200K ARR

Source note: Russia dental market figure from BusinesStat 2026 report. TAM from Mordor Intelligence April 2026. SAM and SOM are team estimates, not verified by third-party research.

7. Product Concept
Core user scenario:
User uploads a selfie or smile photo.
App detects face and mouth area, prepares image for processing.
User selects style: naturally white teeth, straighter shape, soft veneer effect, bright Hollywood-smile.
System generates result. 1 free with watermark, then paid packs.
App shows “Find a clinic near you” button with partner clinics.
Clinic receives warm lead with photo + simulation + contact.

Important: the app must frame results as aesthetic visualization. Cannot promise medical accuracy, treatment plan, treatment prognosis, or guaranteed match with dental procedure outcome.
8. Product Architecture
Component
Role
MVP Approach
Flutter app
iOS/Android interface, photo upload, result, payment, history.
One codebase. UX: upload → style → generate → save → find clinic.
Supabase
Auth, users, history, generation limits, clinic leads.
Quick backend MVP. Photo storage limited by duration.
Backend/API
API key security, photo prep, limits, error logging.
Never call generative APIs from client.
Mouth detection
Detect mouth area, create mask for inpainting.
MediaPipe/YOLO. Test on diverse faces.
Inference provider
Image generation.
Fal.ai or Replicate. Provider abstraction for easy swap.
Payments
Packs, receipts, limits.
YooKassa (RU), Click/Payme (UZ), Apple Pay, Google Pay.
Clinic dashboard
Leads, simulations, branded results.
Phase 2. Simple admin panel.
Analytics
Conversion, cost, success rate, lead quality.
Collect events from day 1.

9. Option 1: Quick Prototype on Ready Models
User uploads selfie, app sends image + prompt to ready model. Model attempts to change smile by text description. Suitable for demo only, not for paid product with quality promises.
Parameter
Assessment
Timeline
2–4 weeks.
Initial cost
~$0–50 excl. team.
Gen cost
$0.05–0.15.
Quality
Good for demo, often unnatural.
Risk
Unstable results.
Verdict
Demo only. Not for paid MVP.
10. Option 2: Inpainting + Flux (Recommended MVP)
System modifies only mouth area. Detects mouth → creates mask → redraws teeth inside mask → preserves face. Best balance of quality, timeline, and cost.
Parameter
Assessment
Timeline
4–6 weeks.
Initial cost
$0–50 for tests.
Gen cost
$0.08–0.20. Must measure.
Servers at launch
$600–1,200/mo at 3K–5K users.
Quality
Good for MVP.
Main risk
Artifacts on complex photos.
Closed beta readiness: 20–30 test selfies, manual quality evaluation, confirmed cost per successful generation, disclaimer texts.
11. Option 3: Custom LoRA on Synthetic Data
Custom synthetic dataset with 3D tooth models + LoRA training. Phase 2 only — after demand validation, paying users, and clear error map from Option 2.
Parameter
Assessment
Timeline
8–12 weeks.
Initial cost
$350–500 for first iteration.
Inference
$800–2,000+/mo.
Quality
Potentially best, needs proof.
Risk
Bad dataset = useless model.

12. Summary Comparison
Criterion
Option 1
Option 2
Option 3
Role
Demo
Recommended MVP
Phase 2 quality boost
Timeline
2–4 weeks
4–6 weeks
8–12 weeks
Initial cost
~$0–50
$0–50
$350–500
Quality
Medium
Good for MVP
Potentially best
Recommendation
Demo only
Launch with this
After validation

13. Unit Economics: Full Model
13.1. B2C Economics (Funnel Validation)
Metric
Conservative
Optimistic
Cost per generation (API)
$0.08–0.12
$0.05–0.08
Failed generation rate
25–30%
15–20%
Effective cost/good gen
$0.11–0.17
$0.06–0.10
Free tier cost (1 gen)
$0.11–0.17
$0.06–0.10
Conversion free → paid
5–8%
10–15%
Avg paid pack revenue
350₽ (~$3.5)
500₽ (~$5)
LTV:CAC ratio
1.5–3x
3–5x

B2C standalone: marginal economics. LTV:CAC below 3x threshold. This confirms B2C = funnel, not business model.
13.2. B2B Economics (Primary Revenue)
Metric
Conservative
Optimistic
Revenue per lead (RU)
500₽
1,500₽
Leads per clinic per month
10–20
30–50
Revenue per clinic/mo
5,000–30,000₽
15,000–75,000₽
Annual value per clinic
60,000–360,000₽
180,000–900,000₽
Cost to serve per clinic/mo
1,000–3,000₽
500–1,500₽
Gross margin
80–90%
90–95%
CAC per clinic
10,000–30,000₽
5,000–15,000₽
Payback
1–6 months
<1 month
LTV:CAC
6–15x
12–30x+
13.3. Path to Break-Even
Milestone
Clinics
Monthly Revenue
Status
Cover infra costs
10–15
50,000–150,000₽
Server + API costs covered
1 FTE salary
25–40
150,000–400,000₽
Developer + support
Sustainable
60–100
400,000–1,000,000₽
Team of 3–4, marketing
Scale
200+
1,000,000₽+
LoRA investment justified

14. MVP Budget by Stages
The following budget covers the full cost of building and launching AI Smile Simulator MVP (Option 2: Inpainting + Flux) including development, infrastructure, testing, legal, and initial marketing. API test costs are low; the real budget is team and development.

14.1. Total Budget Summary
Scenario
Total Budget
Timeline
Assumption
Founders build it themselves
$3,000–5,000
8–10 weeks
Technical co-founder writes code. Budget = infra + API + legal + design.
Outsource to CIS developers
$10,000–18,000
6–8 weeks
Flutter + backend dev at $25–40/hr. 400–500 hours total.
Outsource to agency
$18,000–30,000
6–8 weeks
Full-service agency. Includes UX, dev, QA, deployment.

Recommendation: outsource to 1–2 CIS developers (Russia/Uzbekistan) at $25–40/hr. Budget: $12,000–18,000 for complete MVP including testing phase. This is the sweet spot of cost vs speed vs quality.
14.2. Budget Breakdown by Stage
Stage
What Is Included
Budget
Timeline
1. Discovery & UX
Product scope, user flow, wireframes, UX/UI design (5–8 screens), provider selection
$1,000–2,500
Week 1
2. Core Development
Flutter app (iOS/Android), Supabase backend, photo upload, face detection (MediaPipe), mask generation, Fal.ai inpainting integration, result display
$5,000–9,000
Weeks 2–4
3. Monetization Layer
Payment integration (YooKassa for RU, Click/Payme for UZ), generation limits, pack purchase flow, watermark logic
$1,500–3,000
Week 4
4. Quality Testing
30 test selfies, manual quality evaluation, cost-per-generation measurement, bug fixes, iteration
$500–1,000 (API costs) + dev time
Week 5
5. Legal & Compliance
Privacy policy (152-FZ), medical disclaimer, terms of use, consent flow, data deletion mechanism
$500–1,500
Week 5–6
6. Launch Prep
App Store / Google Play submission ($124), closed beta, feedback collection, partner demo preparation
$300–500
Week 6
7. Initial Marketing
Landing page, 5–10 before/after examples, Instagram/VK content for clinic outreach, first ad test
$500–1,500
Week 6+

Total Stages 1–7: $9,400–19,000 (outsourced) or $3,300–5,500 (founders build).
14.3. Monthly Operating Costs (Post-Launch)
Item
Cost/Month
Notes
Supabase (Pro)
$25
Backend, auth, database, storage
Fal.ai API (inference)
$100–500
At 1,000–5,000 generations/mo. FLUX Pro Fill at $0.05/MP.
Hosting / CDN
$20–50
Static assets, image caching
App Store fees
$10 (amortized)
$99/yr Apple + $25 one-time Google
YooKassa commission
2.8–3.5% of B2C revenue
Payment processing
Support / monitoring
$0–200
Sentry, analytics, basic support
TOTAL
$155–785/mo
Scales with user volume

Break-even on infrastructure: ~20–30 paid B2C packs per month (at 499₽ avg) OR 1–2 clinic partnerships (at 5,000–15,000₽/mo). Infrastructure costs are NOT the bottleneck — user acquisition is.
14.4. Investment Tranches (If Partner Co-Funds)
Tranche
Amount
Trigger
What It Covers
Tranche 1
$5,000–8,000
Decision to start
Development (Stages 1–3): app skeleton + inpainting pipeline
Tranche 2
$3,000–5,000
First working prototype
Testing + legal + monetization (Stages 4–6)
Tranche 3
$2,000–4,000
Quality test passed
Launch prep + initial marketing + first 5 clinic partnerships
Contingency
$2,000–3,000
If needed
Extra iterations, additional testing, unexpected costs
TOTAL
$12,000–20,000

Full MVP from zero to first paying users

15. 6-Week Work Plan for Option 2
Period
What We Do
Result
Week 1
Product scope, UX, provider selection, Flutter/Supabase setup, photo upload.
Working app skeleton.
Week 2
Face/mouth detection, first mask, first inpainting request.
First generation inside app.
Week 3
Improve mask, prompts, image sizing, error handling.
More stable results.
Week 4
History, limits, payment (YooKassa), basic analytics.
User cycle works.
Week 5
Test 20–30 selfies, quality eval, cost measurement.
Go/no-go for beta.
Week 6
Closed beta, feedback, fix failures, prepare partner demo for clinics.
Demo + data + economics.
16. Validation Criteria
% of results rated realistic by user or team.
% with critical artifacts (extra teeth, distorted lips, face changes).
Average generation time.
Cost per successful generation.
Conversion free → paid (B2C).
Number of leads generated for partner clinics (B2B).
Clinic response: how many leads converted to appointments.
Share of users who tap “Find a clinic.”

17. Demo-Pack: Before/After Examples & Quality Criteria
Before any partner meeting, prepare a physical demo-pack that proves the technology works. Words describe; images convince. This section specifies exactly what the demo-pack must contain and how to evaluate quality.
17.1. Demo-Pack Contents
Item
Quantity
Specification
Before/after photo pairs
10 pairs minimum
Diverse set: 5 women + 5 men, ages 20–55, different skin tones, different tooth conditions (yellow, crooked, gaps, missing, healthy). Each pair: original selfie + AI simulation side by side.
Style variations
3–4 per subject
For 3 subjects, show all available styles: natural white, straight, veneer effect, Hollywood smile. Demonstrates range.
Failure examples
3–5
Intentionally include failures: bad lighting, partially closed mouth, side angle. Show what DOESN’T work yet. Honesty builds trust with technical partners.
Quality scorecard
1 table
Summary table rating each example on 5 criteria (see 17.2 below).
Cost data
1 summary
Actual API cost per generation, average attempts per good result, effective cost per successful output.
30-second screen recording
1 video
Phone screen capture: open app → upload selfie → select style → see result. No editing, no narration. Raw UX.
17.2. Quality Evaluation Criteria
Each before/after pair must be rated on these 5 criteria. Scale: 1 (unacceptable) to 5 (excellent). Minimum threshold for launch: average score ≥3.5, no single criterion below 2.
#
Criterion
What to Evaluate
Score 1 (Fail)
Score 5 (Excellent)
1
Tooth realism
Do the teeth look natural? No obvious “photoshop” feeling.
Clearly fake, plastic-looking teeth
Indistinguishable from real teeth in photo
2
Face preservation
Is the rest of the face unchanged? Lips, skin, lighting preserved.
Visible changes to lips, jaw, skin tone, or lighting
Zero detectable changes outside mouth area
3
Boundary blending
Is the edge between original and generated area seamless?
Visible border, “pasted in” look
Seamless transition, no artifacts at mask edge
4
Style accuracy
Does the result match the selected style (whitening vs veneers vs Hollywood)?
Result looks the same regardless of style selection
Clear, distinctive difference between each style
5
Emotional response
Would YOU show this to a friend as “look what I could look like”?
Uncomfortable, uncanny valley
Wow effect, desire to share / show to dentist

The emotional response criterion (#5) is the most important. Technical quality means nothing if the user doesn’t feel “I want this.” A technically imperfect but emotionally compelling result beats a technically perfect but cold one.
17.3. Who Evaluates
Internal team: rate all 10+ pairs on the 5 criteria. Calculate average.
3–5 non-team members (friends/family): show pairs without context, ask “would you pay $5 to get this for yourself?”
1 dentist/orthodontist (if available): evaluate tooth shape realism and clinical plausibility.
Partner: present the scored demo-pack at the meeting. Data, not promises.
17.4. Go / No-Go Decision
Outcome
Average Score
Action
✅ GO
3.5+ overall, no criterion below 2.0
Proceed to closed beta. Show demo-pack to first 5 clinics.
⚠️ CONDITIONAL
3.0–3.4 overall, 1–2 criteria below 2.0
Iterate on pipeline (mask quality, prompts, parameters). Retest in 1 week.
❌ NO-GO
Below 3.0 overall OR 3+ criteria below 2.0
Option 2 pipeline needs fundamental changes. Consider Option 1 for demo only.

18. Risks and Mitigation
Risk
Why It Matters
What to Do
Unrealistic teeth
User won’t pay, won’t trust.
Test on diverse photos. Quality gate before launch.
Negative margin (B2C)
Large packs cost more than revenue.
Start with limited packs + 1 free with watermark. Track COGS.
Face photo privacy
Sensitive data. Error kills trust.
Consent, storage limits, deletion, secure API keys. Russian 152-FZ compliance.
Medical claims
Product perceived as dental recommendation.
Explicit disclaimer: visualization, not diagnosis.
Provider lock-in
API price/quality changes.
Provider abstraction layer.
Bad source photos
Dark, blurry, incomplete uploads.
Pre-generation hints + quality check.
SmileVision / competition
Local B2B competitor with 168+ clinics already exists.
Different category: we are patient acquisition engine, not clinic-side tool. Per-lead = zero risk.
B2C-only trap
Spending budget on $3–5 packs.
Treat B2C as funnel. Pivot to B2B clinics by week 8.
Clinic resistance
Clinics don’t want to pay for leads.
Per-lead = zero risk. Start with 3 free test leads to prove quality.
19. Go-to-Market: Russia & Uzbekistan
17.1. First 15 Clinics — How
Identify 50 cosmetic dentistry clinics in Moscow/SPb via Yandex Maps + ProDoctorov ratings.
Filter: clinics with active Instagram/VK, veneer/whitening focus, modern website.
Direct outreach via Instagram DM or WhatsApp: “We send you patients interested in veneers. You pay only for results. First 3 leads free.”
Offer 3 free test leads to prove quality. No contract, no commitment.
After positive test, sign simple agreement: 500–1,500₽ per lead.
Target: 15 active clinics by month 3 post-MVP.
17.2. Uzbekistan Strategy
Start with 3–5 premium clinics in Tashkent.
Dental tourism angle: patients from Russia/Kazakhstan seeking cheaper veneers.
Lower per-lead pricing: 30,000–50,000 sum per lead.
17.3. Competitive Moat
B2C funnel as acquisition engine — SmileVision and SmileViz don’t have this.
Different category: patient acquisition engine vs dentist-side visualization tool.
Per-lead model = zero risk for clinic (vs SmileVision’s 3,000–30,000 ₽/mo fixed subscription).
Phase 2: LoRA trained on CIS faces for better quality on local demographics.

20. What Is Required from Partners
This section specifies exactly what the project needs from partners at each stage. Not a discussion list — a concrete ask.
20.1. Partner Contribution Options
Partners may participate in one or more of the following roles:
Role
What Partner Provides
Why It Matters
Financial partner
Co-fund MVP development ($5,000–10,000 as Tranche 1)
Covers development costs; shares risk and upside.
Clinical partner
Access to 3–5 dental clinics for pilot testing
Provides real test environment, quality feedback, first B2B customers.
Dental expert
Stomatologist/orthodontist for quality evaluation
Validates tooth realism; adds clinical credibility to product.
Marketing partner
Access to dental industry network, conferences, media
Accelerates clinic acquisition; opens B2B distribution.
Technical partner
Development team or co-development capacity
Builds the product; maintains and iterates post-launch.
20.2. What We Ask at This Meeting
The purpose of this brief is to reach three decisions:

Decision 1: Do we proceed? Confirm interest in the AI Smile Simulator concept and the B2B per-lead revenue model for Russia/Uzbekistan.
Decision 2: What is each partner’s role? Define who contributes what: funding, clinic access, dental expertise, development, marketing.
Decision 3: Approve Tranche 1 budget. Release $5,000–8,000 to begin development of the MVP (Stages 1–3: app skeleton + inpainting pipeline). Timeline: 4 weeks to first working prototype.
20.3. What Partners Get in Return
Milestone
Partner Receives
Timeline
After Tranche 1
Working prototype: upload selfie → see AI smile simulation. Internal demo.
Week 4
After Tranche 2
Scored demo-pack (10+ before/after pairs). Quality data. Cost-per-generation confirmed.
Week 5–6
After Tranche 3
Closed beta with first 3–5 clinic partnerships. First B2B revenue. User feedback data.
Week 8–10
Month 3
Go/no-go decision on scaling. Data on: lead quality, clinic conversion, unit economics.
Month 3
20.4. Specific Asks for This Meeting
Confirm interest in the concept and the per-lead B2B model.
Agree on partner roles (funding / clinics / expertise / development / marketing).
Approve Tranche 1 budget: $5,000–8,000 for development start.
Provide or help source: 1 stomatologist for quality evaluation, 3 pilot clinics in Moscow/SPb.
Collect 20–30 test selfies (diverse: age, gender, lighting, tooth condition) for quality testing.
Assign legal responsibility: 152-FZ compliance, medical disclaimer, consent flow.
Set next meeting date: 4 weeks from today, to review the working prototype.

What we are NOT asking: we are not asking for a large investment before the product is proven. Tranche 1 ($5K–8K) builds a working prototype. Tranche 2 ($3K–5K) is released ONLY if the prototype passes quality testing. Total risk exposure before validation: $8K–13K. If quality test fails, we stop and reassess.
21. Conclusion
Best path for launch: manageable MVP (Inpainting + Flux), 1 free generation with watermark, limited B2C packs in rubles, and B2B per-lead monetization through dental clinics.
Global analysis confirms: no successful AI smile tool lives on consumer revenue. All five top competitors monetize through clinics. Russia and Uzbekistan have zero direct competitors — this is the window.
Revenue model: B2C app generates awareness and leads. Clinics pay 500–1,500₽ per warm lead. Phase 2: widget on clinic websites. Phase 3: SaaS subscription. Per-lead model has zero entry barrier for clinics and proven 20–50x ROI.

Partner formulation: “We build a mobile app that shows users their future smile. Users who want to make it real get connected to partner clinics. Clinics pay us per patient lead. We are the first AI smile platform in the CIS market.”

Version 2.4. Working document for partner discussion. 28.06.2026 | Bali
