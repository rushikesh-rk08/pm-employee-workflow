# Sprint brief: 2026-11-student-housing-sample.md

**Goal:** Raise the share of students who complete a booking after shortlisting a room.

Generated on 2026-11-13 by PM Employee using `gemini-3.6-flash`. Evidence check: 8 of 8 quotes found word for word in the feedback.

## 1. Insights

### Price Discrepancy & Hidden Checkout Fees

Students experience distrust and abandon bookings because final costs change at checkout without explanation or clear upfront fees.

> "The total price changed between the listing page and the payment page and nobody explained why."

> "Please show the full cost upfront. Hidden fees at the end made me distrust the listing."

### Document Upload Failures on Mobile

Technical failures during document upload and incorrect status indicators on mobile prevent users from completing their application.

> "This year the document upload failed three times on my phone."

> "I uploaded my passport twice and the page still says document missing."

### Guarantor Process Friction & Lack of Upfront Context

Students are caught off guard by guarantor requirements at the final step and drop out due to lengthy, complex forms.

> "I did not understand what a guarantor was until I was already at the last step."

> "I gave up at the guarantor form. Too many fields and I did not have the details with me."

### Shortlist Evaluation and Payment Delegation Gaps

Students lack tools to compare shortlisted rooms side by side and cannot easily delegate deposit payments to parents.

> "I shortlisted four rooms but could not compare them side by side, so I ended up making my own spreadsheet."

> "I needed my parents to pay the deposit but there was no way to send them the payment link."

## 2. User stories

### 1. Upfront Full Cost Display on Listings

As a student viewing a room listing, I want to see the complete total price breakdown upfront, so that I am not surprised by unexpected fee changes on the payment page.

Acceptance criteria:

- [ ] Display an itemized breakdown of all mandatory fees on the room listing page.
- [ ] Ensure the total calculated price on the listing page matches the final charge on the payment page exactly.

### 2. Side-by-Side Shortlist Room Comparison

As a student with multiple saved rooms, I want to compare my shortlisted rooms side by side, so that I can make a decision without manually building a separate spreadsheet.

Acceptance criteria:

- [ ] Allow users to select up to 4 shortlisted rooms for side-by-side comparison.
- [ ] Display key attributes (price, location distance, inclusions) in a grid view.

### 3. Third-Party Payment Link for Deposits

As a student completing a booking, I want to generate and send a deposit payment link to my parents, so that they can pay the fee directly on my behalf.

Acceptance criteria:

- [ ] Include a 'Share payment link' option at the deposit payment step.
- [ ] Allow third parties to access a secure checkout page via the shared link to complete payment.

### 4. Mobile Document Upload Fix and Real-Time Status Update

As a mobile user uploading verification documents, I want the upload process to succeed reliably and update my status immediately, so that I can finish my booking.

Acceptance criteria:

- [ ] Ensure document uploads (e.g. passport) complete successfully on mobile browsers.
- [ ] Update the document status indicator to 'Uploaded' immediately after successful file upload.

## 3. Stakeholder email

**Subject:** Sprint Plan: Boosting Shortlist-to-Booking Conversion

Hi Team,

Our next sprint focuses on driving higher conversion from room shortlisting to completed bookings by addressing key friction points identified in recent customer feedback.

Key deliverables include:
1. Upfront Pricing Transparency: Showing complete cost breakdowns on listings to prevent checkout abandonment.
2. Shortlist Comparison View: Enabling side-by-side room comparison so students do not rely on external spreadsheets.
3. Third-Party Payment Links: Allowing students to send deposit links directly to parents.
4. Document Upload Fixes: Resolving mobile upload failures and status sync issues.

By fixing these UX barriers and technical failures, we aim to deliver a smoother path to payment.

Best regards,
Product Team

## 4. Risks

| Severity | Risk | Mitigation |
| --- | --- | --- |
| High | Inventory data inconsistency between support channels and actual room availability causes sold-out bookings after customer payment. | Sync real-time room availability across customer chat tools and booking engines automatically. |
| Medium | Contradictory details between listing descriptions and contract terms (such as utility bill coverage) destroy user trust. | Audit listing data models to ensure contract terms dynamically mirror listing attributes. |
| Low | High dropout rates on guarantor forms due to excessive fields and lack of upfront explanation. | Introduce early educational tooltips about guarantor requirements and implement a draft-save feature on the form. |
