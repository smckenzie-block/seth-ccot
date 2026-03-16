---
name: ccot-response-drafter
description: CCOT Response Drafter — Draft a Formal Complaint Response letter for the Cash Complaint Operations Team (CCOT) using JIRA investigation notes. Automatically selects and fetches the correct template from the full template library.
---

# CCOT Response Drafter

This skill helps CCOT complaint handlers draft a Formal Complaint Response — the final written letter sent to a consumer in reply to a regulatory complaint (e.g., CFPB). The handler provides a JIRA key, and the skill automatically selects the correct template from the CCOT template library, fetches it, extracts the investigation findings, and produces a complete draft response that follows the team's established format, tone, and style guide.

This skill focuses exclusively on drafting. For a Legal and Compliance risk review of a completed draft, use the companion skill `ccot-compliance-reviewer`.

## When to Use This Skill

Use this skill when a complaint handler says something like:
- "Draft a formal response for CCOT-XXXXX"
- "Write the complaint response for this JIRA"
- "Help me draft the final response letter"
- "Draft a response using this JIRA and this template" (handler may optionally provide a template link)

## Inputs Required

The complaint handler must provide:
1. **JIRA Issue Key or URL** — e.g., `CCOT-30543` or `https://block.atlassian.net/browse/CCOT-30543`

The complaint handler may optionally provide:
2. **Google Document Template Link** — if the handler provides a specific template link, use that template instead of auto-selecting. If not provided, the skill will automatically select the best template from the library.

## Supporting Files

This skill includes the following supporting files in its directory:

- **`template_catalog.json`** — A structured catalog of all 50 current (2026) regulatory response templates, organized into 14 categories with keyword matching rules, Google Doc IDs, and usage guidance for each template.
- **`fetch_template.py`** — A Python helper script that fetches a Google Doc template by its document ID using the Google Drive API. It handles OAuth token refresh automatically via the macOS keychain.

## Steps

### Step 1: Extract Investigation Notes from JIRA

1. Parse the JIRA issue key from the provided link (project key is `CCOT`).
2. Retrieve the issue fields:
   - `summary` — complaint title (format: `[Agency] [ComplaintID] [Name]`)
   - `customfield_11579` — Complaint ID
   - `customfield_11569` — Date of Receipt of Complaint
   - `customfield_11578` — Due Date of Response
   - `customfield_11567` — Google Drive Link
   - `assignee` — complaint handler
   - `issuetype` — Bug, Regulatory, or Pre-Litigation
3. Retrieve **all comments** on the issue (these contain the investigation notes).
4. From the comments, extract the structured investigation data. The investigation comment follows this standard format:
   - **Complaint ID** — CCN number linked to CF1/Salesforce
   - **Relevant Account(s)** — Regulator and Toolbox links
   - **PII Review** — PII VERIFIED or PII NOT VERIFIED, with individual field checks (Name, Phone, Email, Zip Code, etc.)
   - **Complaint Summary** — Bullet points of what the customer alleges and their requested resolution
   - **Related Complaints** — Links to prior complaints (if any)
   - **Relevant Transactions** — Dollar amounts, dates, transaction types, and links
   - **Review** — CF1 support case history, dispute details, escalation outcomes
   - **Investigation Actions** — Escalations to Disputes/SMEs/Compliance, manual reimbursements
   - **TL;DR** — Condensed summary with recommended next steps and template reference
   - **Closing tag** — `#CCOT_INV_ACCT_REVIEWED_CCN-XXXXXXX`
5. Also check for any follow-up comments (e.g., "Response sent [date]" or escalation updates).

### Step 2: Select and Fetch the Template

This step uses the **template catalog** (`template_catalog.json`) to automatically select the correct template. Follow these rules in order:

#### 2a: If the Handler Provided a Template Link

If the handler provided a Google Document link, use that template directly:
1. Extract the Google Doc ID from the URL (format: `https://docs.google.com/document/d/{DOC_ID}/edit`).
2. Fetch the template content by running the helper script:
   ```
   python3 <skill_directory>/fetch_template.py <DOC_ID>
   ```
3. Skip to Step 3.

#### 2b: Automatic Template Selection (No Template Link Provided)

If the handler did NOT provide a template link, automatically select the best template:

1. **Read the template catalog** from `template_catalog.json` in this skill's directory.

2. **Check the TL;DR first.** If the investigation notes TL;DR explicitly names a template (e.g., "Use the P2P - Cancel Authorized Payment template"), match it to the catalog by name and use that template.

3. **Check for special routing conditions** (in this priority order):
   - If this is a **duplicate complaint** (TL;DR says "duplicate" or "already responded") → use `Duplicate Complaint - Reg- Template 2026` or `SR Duplicate CFPB Complaint Template 2026`
   - If **PII is NOT VERIFIED** → use `SR IDV / PII Mismatch Template 2026`
   - If the complaint is from **MA DOB** (Massachusetts Division of Banks) → use `MA DOB template 2026`
   - If the complaint is from a **UK customer** → use `UK Based Complaint - Template 2026`
   - If the complaint is from a **state agency** and requires a privacy notice → use `State Agency - NMI / Privacy Notice Response - Template 2026`
   - If Cash App **needs more information** (NMI) and no specific topic template applies → use `NMI / Contact Support - Template 2026`

4. **Match by complaint topic.** Analyze the complaint summary and investigation notes to identify the primary topic. Match against the catalog categories using the `keywords` arrays:

   | Complaint Topic | Category to Check |
   |----------------|-------------------|
   | Account access, locked out, identity verification | Account Access |
   | Account closed, banned, suspended, denylisted | Account Closed / Denylisted |
   | Hacked, unauthorized access, ATO, compromised | ATO (Account Takeover) |
   | Bitcoin, crypto, BTC | Bitcoin |
   | Cash App Card, debit card, merchant, ATM | Cash App Card |
   | Cash Out, Add Cash, bank transfer | Cash Out / Add Cash |
   | Direct deposit, payroll, paycheck | Direct Deposit |
   | Frozen balance, garnishment, sanctions | Frozen Balance |
   | Identity theft, fraudulent account, 1099-K | ID Theft |
   | P2P payment, sent money, scam, wrong person | P2P (Peer-to-Peer) |
   | Business account, Cash for Business | Other / Specialty |
   | Deceased customer | Other / Specialty |
   | Mobile check, paper money deposit | Other / Specialty |

5. **Match by outcome within the category.** Once the category is identified, select the specific template based on the investigation outcome:
   - Was the claim **approved/resolved** or **denied**?
   - Was a **reimbursement issued** or not?
   - Is the investigation **ongoing**?
   - Was the account **reinstated** or still closed?
   - Was the issue related to a **chargeback**, **misdirected payment**, or **unauthorized transaction**?

   Use the `use_when` field in each template entry to make the final selection.

6. **Fallback.** If no specific template matches, use `Blank - Template 2026`.

7. **Ambiguity handling.** If two or more templates seem equally appropriate, present the top candidates to the handler with a brief explanation of each and ask them to choose. Example:
   > "Based on the investigation notes, this complaint could use either:
   > 1. **ATO - Confirmed - Reimbursement** — if the ATO was confirmed and the customer was reimbursed
   > 2. **ATO - Confirmed/Denied - No Reimbursement** — if the ATO was confirmed but no reimbursement was issued
   >
   > Which template should I use?"

#### 2c: Fetch the Selected Template

Once a template is selected (either by handler link or auto-selection):

1. Get the Google Doc ID from the catalog entry or the handler's link.
2. Fetch the template content by running:
   ```
   python3 <skill_directory>/fetch_template.py <DOC_ID>
   ```
   Replace `<skill_directory>` with the actual path to this skill's directory (e.g., `~/.config/goose/skills/ccot-response-drafter/`).
3. If the fetch fails (e.g., token expired, network error), fall back to asking the handler to paste the template text or provide a downloaded copy.
4. Confirm the template selection with the handler:
   > "I've selected the **[Template Name]** template based on the investigation notes. Proceeding with drafting."

### Step 3: Draft the Response

Using the investigation notes and the template structure, draft the Formal Complaint Response following these rules:

#### Document Structure (Mandatory — All Responses)

Every response letter MUST follow this exact four-section structure:

```
[Date]
[Customer Full Name]
[Address Line 1]
[Address Line 2 — City, ST  ZIP]

Re: Consumer Complaint No.: [Complaint ID from customfield_11579]

Dear [Customer Full Name],

This letter is Cash App's ("Cash App," "we," "our" or "us") written reply to your [Date of Receipt], complaint to the [Regulatory Agency Name] concerning our Cash App service.

I. Introduction
[Standard boilerplate — do not modify]

II. Your Complaint
[Paraphrase of the customer's complaint from the investigation notes]

III. Our Investigation
[Findings from the investigation, support case history, dispute outcomes]

IV. Conclusion
[Summary of findings, next steps if any, closing guidance]

We encourage you to review Cash App's Terms of Service on our official website. We hope this response satisfactorily addresses your complaint.

Sincerely,
Cash App Complaint Operations Team
```

#### Section I — Introduction (Standard Boilerplate)

Always use this exact text:

> We are a financial services and technology company that offers products and services to businesses and individuals. Cash App is designed to create an ecosystem of tools for individuals, enabling them to electronically store, send and receive money, among other capabilities.

#### Section II — Your Complaint (Writing Rules)

- **Source:** Use the "Complaint Summary" and/or "TL;DR" from the investigation notes.
- **Voice:** Write in second person, **active voice** ("Your complaint states that you sent…", "You assert that…", "Your complaint further requests that…").
- **Tone:** Formal, omniscient, specific to the task. Never argumentative or dismissive.
- **Content:** Paraphrase the customer's claims accurately. Include:
  - What happened (dates, amounts, transaction types)
  - What the customer tried to do about it (contacted support, filed disputes)
  - What the customer is requesting (refund, account reinstatement, etc.)
- **Do NOT** include internal investigation findings in this section — only the customer's stated version of events.
- **Do NOT** include internal tool links, customer tokens, or internal system references.
- **Direct quotes:** When quoting the complainant, do so respectfully. Use quotes that accurately reflect what the customer alleges and requests. Do NOT include direct quotes specifically to make the complainant look foolish. Pull quotes verbatim from the complaint, but it is acceptable to use brackets (e.g., `[ ]`) to edit pronouns, add small transitory words, or make light edits for cohesion and clarity.
  - Example: *Your complaint claims "[your] phone was stole[n]"* is acceptable when the original text said *"my phone was stole"*

#### Section III — Our Investigation (Writing Rules)

- **Source:** Use the "Review", "Investigation Actions", and "TL;DR" sections from the investigation notes.
- **Voice:** Write from Cash App's perspective in **active voice**, following the pattern: "on [date] > [person/entity] did > [action] > but, [result]".
  - ✅ *"On January 1, 2026, you sent $100.00 to the recipient for payment for goods or services that turned out to be a scam."*
  - ❌ *"On January 1, 2026, a payment was sent between you and the recipient."*
  - ✅ *"On January 1, 2026, you sent $100.00 worth of Bitcoin to an external wallet…"*
  - ❌ *"On January 1, 2026, $100.00 worth of Bitcoin was sent to an external wallet…"*
- **Content:** Include:
  - Support case history (dates, channels — see channel formatting rules below)
  - Dispute filing and outcome details (dates filed, dates resolved, outcomes)
  - Any escalations and their results
  - Any reimbursements or credits issued (amounts, dates)
  - Communications sent to the customer (dates, channels, content summary)
- **Chronological order** is preferred when recounting support interactions.
- **Do NOT** include internal links, Slack threads, Regulator/Toolbox URLs, customer tokens, or internal tool names.
- **Do NOT** disclose internal investigation reasoning that is marked "Do not disclose or share with customers."
- **Do NOT** reference internal team names (e.g., "ATO team", "CERT", "MET Team", "Denylist Appeals Team"). Instead use "Cash App Support", "a Cash App specialist", "a Cash App Support manager", or "a member of our team".
- **Replace** internal jargon:
  - "CF1 case" → "our records"
  - "Regulator/Toolbox" → omit entirely
  - "comms" → "communications" or "correspondence"
  - "cx" / "Cx" → "you" (in second person) or "the customer"
  - "NMI" → "requested additional information" or "reached out to you"
  - "denylisted" → "closed" or "suspended" (depending on context)
  - "Matter Closed WF" → omit; just state the outcome

#### Section IV — Conclusion (Writing Rules)

- **Summarize** the key findings from Section III in one to three sentences.
- **State the final outcome clearly** (claim denied, credit issued, investigation ongoing, etc.).
- **Include next steps** if applicable:
  - If the customer can appeal: provide instructions
  - If the customer should contact support: provide contact info (app, website cash.app/contact, phone 1-800-969-1940)
  - If law enforcement is relevant: include the standard law enforcement paragraph
  - If no further action: state clearly
- **Always end with:** "We encourage you to review Cash App's Terms of Service on our official website. We hope this response satisfactorily addresses your complaint."

#### Template-Specific Guidance

When filling in the template, follow these conventions:

- **ZZZ placeholders:** All `ZZZ...ZZZ` markers in templates are fill-in fields. Replace every one with the appropriate information from the investigation notes.
- **Optional sections:** Text enclosed in `ZZZZ Option A: ... ZZZZ` / `ZZZZ Option B: ... ZZZZ` blocks means choose the appropriate option and delete the other.
- **Conditional paragraphs:** Text enclosed in `ZZZZ ... ZZZZ` that contains instructions (e.g., "If the customer has appealed...") should be included or removed based on the investigation facts.
- **Regulatory agency:** Match the agency from the JIRA summary:
  - "CFPB" → "Consumer Financial Protection Bureau"
  - "NY AG" → "New York Attorney General"
  - "MA DOB" → use the MA DOB-specific template
  - Other state agencies → use the appropriate state agency template

---

## Style Guide

### Formatting Specifications

| Element | Font | Weight | Size |
|---------|------|--------|------|
| **Document Body** | Montserrat | Normal | 11pt |
| **Footnotes** | Montserrat | Normal | 10pt |
| **Excerpted Text** | Montserrat | Normal | 10pt |

### Active Voice (Mandatory)

Write all responses in narrative form using **active voice**, following the structure: **"on [date] > [person] did > [action] > but, [result]"**.

✅ *"On January 1, 2020, you sent $100.00 to the recipient for payment for goods or services that turned out to be a scam."*
❌ *"On January 1, 2020, a payment was sent between you and the recipient."*

✅ *"On January 1, 2020, you sent $100.00 worth of Bitcoin to an external wallet…"*
❌ *"On January 1, 2020, $100.00 worth of Bitcoin was sent to an external wallet…"*

### Date Format

Always write dates in **Month Name Day, Year** format. If a date appears mid-sentence, a comma must also follow the year.

✅ July 1, 2020
✅ "On October 13, 2022, a Cash App specialist informed you…"
❌ 7/1/20
❌ 7.20.2021
❌ July 01, 2020 (no leading zero on the day)

### Currency Format

Always write transaction amounts as the **full dollar amount including decimals**.

✅ $100.00
❌ $100

Use commas for thousands: $1,300.00, $2,037.36

### Address Format

- Use the **2-character state abbreviation** (e.g., MO, IL, CA).
- Place **2 spaces** between the state abbreviation and the zip code.
- Use only the **first 5 digits** of the zip code.
- When adding a Suite/Apt/Bldg number, place it at the **end of the delivery address line**.

✅ `Los Angeles, CA  90048`
❌ `Los Angeles, California, 90048-1234`

✅ `42 Wallaby Way Apt 101`
❌ `42 Wallaby Way, Apartment 101` (on a separate line)

### Support Channel References

When referencing how the customer contacted Cash App Support, use these specific phrasings:

| Internal Term | Response Phrasing |
|---------------|-------------------|
| Messaging / Chat / Live Chat | **"via Live Chat"** |
| Voice / Phone | **"directly, via phone"** |
| Email | **"via email"** |
| In-app notification | **"via in-app notification"** |

✅ *"You reached out to Cash App Support via Live Chat."*
✅ *"You reached out to Cash App Support directly, via phone."*
❌ *"You reached out to Cash App Support via phone."*
❌ *"You reached out to Cash App Support through chat."*

### Pronouns

- **Default to gender-neutral pronouns** (they/them/their) when referring to third parties.
- Only use gendered pronouns when referring to a complainant if they were **affirmatively provided in the complaint**.
- When writing in second person to the complainant, use "you/your" (this avoids the pronoun issue entirely for the primary addressee).
- **Avoid overuse of pronouns.** Name the referent where possible and appropriate.
  - ❌ *"They sent them to stakeholders on Wednesdays."*
  - ✅ *"The Complaints Analyst sends the reports to stakeholders on Wednesdays."*

### Typo Corrections

If the complainant made an **obvious typo** in their complaint (e.g., "Las Angeles" instead of "Los Angeles"), correct the information in the final response draft. Do not reproduce the error.

### Direct Quotes from Complainant

- Use quotes that **accurately reflect** what the customer alleges and requests.
- **Do NOT** include direct quotes specifically to make the complainant look foolish.
- Pull quotes **verbatim** from the complaint when possible.
- It is acceptable to use **brackets** (`[ ]`) to:
  - Edit pronouns
  - Add small transitory words
  - Make light edits for cohesion and clarity

✅ *Your complaint claims "[your] phone was stole[n]."* (original: "my phone was stole")
❌ Reproducing grammatical errors without correction when they could embarrass the complainant

### Footnotes for Cash App Terminology

Whenever using Cash App-specific terminology in the response, **explain the term using a footnote**. Common terms requiring footnotes include:

- **Cash Out** — the process of transferring funds from a Cash App balance to a linked bank account or debit card
- **Add Cash** — the process of adding funds from a linked bank account or debit card to a Cash App balance
- **P2P payment** — a peer-to-peer payment sent between Cash App users
- **$cashtag** — a unique identifier used to send and receive payments on Cash App

Many approved definitions exist in the `regd` and `litd` TextBlaze snippets. These definitions have been approved by legal counsel and **should not be changed without written permission** from legal by tagging them in the document. When drafting, use the standard approved definitions. If a term's approved definition is unknown, flag it with `[HANDLER: please confirm approved footnote definition for "[term]"]`.

Footnotes should be formatted in **Montserrat, Normal weight, 10pt**.

---

## Grammar Rules

### Abbreviations and Acronyms

Spell out terms upon **first use** and include the acronym or abbreviation in parentheses. Use the abbreviation or acronym thereafter.

✅ First use: *"Consumer Financial Protection Bureau ("CFPB")"* → subsequent uses: *"CFPB"*
✅ First use: *"peer-to-peer ("P2P")"* → subsequent uses: *"P2P"*

### Ampersand

Use an ampersand (`&`) only when it is part of an official title. Otherwise, spell out "and."

✅ *UK & Ireland Cash Complaint Program* (official title)
✅ *"…your dispute request and initiated a claim…"* (body text)
❌ *"…your dispute request & initiated a claim…"*

### Company Names

- **Block, Inc.** — The official name of the parent company. Always place a comma between "Block" and "Inc." and always follow "Inc." with a period. On first use in a document, write the full name followed by a parenthetical note (e.g., *Block, Inc. and its subsidiaries (herein referred to as "Block")*). Avoid using Block as a possessive.
  - ✅ *Block employees*
  - ❌ *Block's employees*
- **Cash App** — Do not refer to Cash App as simply "Cash." Avoid using Cash App as a possessive.
  - ✅ *Cash App employees*
  - ❌ *Cash App's employees*
  - ❌ *Cash employees*

### Capitalization

- Always capitalize the first letter of every sentence.
- Capitalize the first letter of proper nouns.
- Capitalize all words in titles **except** articles, prepositions, and conjunctions.
- Capitalize official role names (e.g., Advocates, Associates, Governance Specialist).
- Capitalize official business unit names (e.g., Voice, Social, Messaging).
- Capitalize product names (e.g., Cash App, Cash App Taxes, Lending).
- Capitalize line-of-business names (e.g., Square, Square Financial Services, Tidal).

### Commas (Oxford Comma Required)

Use the **Oxford comma** (serial comma). Always place a comma before "and" or "or" in a series of three or more elements.

✅ *"…your account history, transaction disputes, and other possible violations…"*
❌ *"…your account history, transaction disputes and other possible violations…"*

### Contractions

**Do not use contractions.** Write out all words in full.

✅ *"do not"*, *"we are"*, *"you will"*, *"it is"*, *"cannot"*
❌ *"don't"*, *"we're"*, *"you'll"*, *"it's"*, *"can't"*

### Dates

Use the format **Month Name Day, Year** (e.g., October 13, 2022). Do not use numeric date formats. If the date appears mid-sentence, a comma must also follow the year.

✅ *"On October 13, 2022, a Cash App specialist informed you…"*
❌ *"On 10/13/22 a Cash App specialist informed you…"*

### Exclamation Marks

**Do not use exclamation marks.** The tone is formal and measured at all times.

### Jargon and Slang

**Do not use jargon or slang.** All language must be clear, professional, and accessible to a general audience. See the internal jargon replacement table in Section III writing rules for specific substitutions.

### Numbers

- **Spell out numbers under 10** in most instances (e.g., "three disputes," "one transaction").
- **Always write out numbers at the beginning of sentences** (e.g., "Twelve transactions were reviewed…").
- **Exceptions:** Percentages, dates, times of day, prices, and currency amounts may use numerals regardless of value (e.g., "$5.00," "2:00 PM," "3%").

### Periods

- Use a **single space** after periods.
- Place periods **inside** quotation marks.
  - ✅ *Cash App refers to this as "Cash Out."*
  - ❌ *Cash App refers to this as "Cash Out".*

### Point of View

- The response letter is written in **second person** when addressing the complainant ("you," "your").
- When referring to Cash App's actions, use **first person plural** ("we," "our," "us").
- Internal documentation and process descriptions use **third person**.

### Quotation Marks

- **Periods and commas** go **inside** quotation marks.
- **All other punctuation** (colons, semicolons, question marks, exclamation marks) goes **outside** quotation marks, unless it is part of the direct quote.

✅ *You stated that Cash App "refused to help."*
✅ *Did you state that Cash App "refused to help"?*
❌ *You stated that Cash App "refused to help".* (period outside)

### Sentences

Write in **complete sentences**. Avoid sentence fragments. Every sentence must have a subject and a predicate.

### Tense

- Use **present tense** as the default.
- **Avoid future tense.** Do not write "we will investigate" — instead write "we have investigated" or "Cash App investigates."
- **Avoid switching tenses** within a paragraph. When recounting past events in Section III, past tense is appropriate and should remain consistent throughout the narrative.

### Terminology Consistency

Use **consistent terminology** throughout the entire document. Once a term is introduced, use the same term every time.

- ✅ Always refer to "Cash App Support" — do not alternate with "customer service," "support team," "help desk," etc.
- ✅ If you introduce "peer-to-peer ("P2P") payment" on first use, use "P2P payment" consistently thereafter.
- ✅ Always refer to the complainant as "you" — do not alternate with "the customer," "the complainant," etc. within the same letter.

### Tone

**Formal, omniscient, and specific to the task.** The response should convey authority, thoroughness, and professionalism. It should demonstrate that Cash App has carefully reviewed the complaint and conducted a complete investigation.

### Voice

**Active voice is mandatory.** Rewrite any passive constructions into active voice.

✅ *"A Cash App specialist informed you via email on March 5, 2026, that your claim had been denied."*
❌ *"You were informed via email on March 5, 2026, that your claim had been denied."*

✅ *"Cash App issued a permanent credit of $290.00 to your account balance."*
❌ *"A permanent credit of $290.00 was issued to your account balance."*

---

## Chicago Manual of Style Alignment (18th Edition)

The Formal Complaint Response must align with the Chicago Manual of Style ("CMOS"), 18th edition (University of Chicago Press, 2024), the authoritative American English style guide used across publishing, corporate communications, and legal correspondence. The following rules from CMOS are incorporated into the drafting process and supplement the team's existing grammar rules. Where the team's internal style guide provides a more specific rule (e.g., address formatting, support channel phrasing), the internal rule takes precedence. Where the internal guide is silent, CMOS governs.

### Punctuation (CMOS Chapter 6)

- **Serial (Oxford) comma:** Always use the serial comma before "and" or "or" in a series of three or more elements. (CMOS 6.19) — *Already encoded in team grammar rules.*
- **Comma after introductory elements:** Use a comma after introductory adverbial phrases and clauses. (CMOS 6.24)
  - ✅ *"On February 25, 2026, you contacted Cash App Support."*
  - ❌ *"On February 25, 2026 you contacted Cash App Support."*
- **Comma before "which" in nonrestrictive clauses:** Use a comma before "which" when introducing a nonrestrictive (nonessential) clause. Do not use a comma before "that" in restrictive clauses. (CMOS 6.27)
  - ✅ *"Cash App canceled the transaction, which occurred on February 2, 2026."*
  - ✅ *"The transaction that occurred on February 2, 2026, has been reviewed."*
- **Em dash usage:** Use em dashes (—) sparingly and without spaces to set off amplifying or explanatory elements. Do not use hyphens or en dashes in place of em dashes. (CMOS 6.87)
- **Colon usage:** Use a lowercase letter after a colon if what follows is not a complete sentence. Capitalize the first word after a colon if it introduces a complete sentence or multiple sentences. (CMOS 6.63)
- **Semicolons in complex lists:** Use semicolons to separate items in a series when one or more items contain internal commas. (CMOS 6.60)
- **Periods with quotation marks:** Periods and commas always go inside closing quotation marks. Colons and semicolons go outside. Question marks and exclamation marks go inside only if they are part of the quoted material. (CMOS 6.9) — *Already encoded in team grammar rules.*

### Spelling and Hyphenation (CMOS Chapter 7)

- **Compound modifiers before a noun:** Hyphenate compound modifiers that precede a noun (e.g., "in-app notification," "third-party vendor"). Do not hyphenate when the compound follows the noun (e.g., "the notification was in app"). (CMOS 7.85)
- **Prefixes:** Generally, do not hyphenate words with prefixes (e.g., "nonrefundable," "unauthorized," "reimbursement"). Hyphenate when the prefix precedes a capitalized word or a numeral (e.g., "pre-2026"). (CMOS 7.85)
- **"Email" not "e-mail":** Per CMOS 18th edition, "email" is written without a hyphen. (CMOS 7.89, Section 3)
- **"Internet" is lowercase:** Per CMOS 18th edition, "internet" is lowercase unless at the start of a sentence.

### Numbers (CMOS Chapter 9)

- **Spell out numbers one through nine** in running text. Use numerals for 10 and above. (CMOS 9.2) — *Team rule says "under 10," which aligns.*
- **Always use numerals for:** Currency amounts, percentages, dates, times of day, addresses, and page numbers. (CMOS 9.19–9.24)
- **Spell out numbers at the beginning of a sentence.** If the number is unwieldy when spelled out, rewrite the sentence. (CMOS 9.5)
  - ✅ *"Twenty-four disputes were filed on your behalf."*
  - ❌ *"24 disputes were filed on your behalf."* (at start of sentence)
- **Use commas in numbers of four or more digits:** $1,050.00, not $1050.00. (CMOS 9.55)

### Names and Terms (CMOS Chapter 8)

- **Titles of works:** Italicize titles of published works (books, reports, legislation titles). Use quotation marks for shorter works (articles, chapters). (CMOS 8.163–8.178)
- **Proper nouns:** Always capitalize proper nouns, including product names (Cash App, Cash App Card), company names (Block, Inc.), and regulatory agency names (Consumer Financial Protection Bureau). (CMOS 8.1)
- **Generic terms lowercase:** When referring to generic concepts, use lowercase (e.g., "your account," "the transaction," "the dispute"). (CMOS 8.1)

### Possessives (CMOS Chapter 7)

- **Singular possessives:** Form the possessive of most singular nouns by adding 's, even if the noun ends in "s" (e.g., "Congress's," "the witness's"). (CMOS 7.17)
- **Note:** Cash App and Block, Inc. should not be used as possessives per the team's internal style guide. This CMOS rule applies to other nouns in the response.

### Singular "They" (CMOS 18th Edition)

- CMOS 18th edition expands acceptance of singular "they" and "their" as gender-neutral pronouns. Use singular "they" when referring to a person whose gender is unknown or when the complainant has not provided gendered pronouns. (CMOS 5.48) — *Already encoded in team pronoun rules.*

---

## Readability Standards (6th–8th Grade Level)

### Target Reading Level

All Formal Complaint Response letters must be written at a **6th to 8th grade reading level** as measured by the Flesch-Kincaid Grade Level formula. This aligns with the Consumer Financial Protection Bureau's own plain language guidance and industry best practices for consumer-facing financial correspondence.

The readability standard is based on the **Flesch-Kincaid Grade Level** test, a teacher-adopted, academically validated readability formula developed by Rudolf Flesch and J. Peter Kincaid. The formula is:

> **Flesch-Kincaid Grade Level** = 0.39 × (total words / total sentences) + 11.8 × (total syllables / total words) − 15.59

A score of **6.0 to 8.0** means the text is easily understood by an average 6th to 8th grade student. This is the industry-recommended range for consumer financial communications.

As a secondary reference, the **Dale-Chall Readability Formula** (Dale and Chall, 1948; revised 1995) may also be used. The Dale-Chall formula uses a list of 3,000 words that fourth-grade American students can reliably understand. A Dale-Chall adjusted score of **6.0 to 6.9** corresponds to 7th–8th grade comprehension, which aligns with the target range.

**Source:** Chall, Jeanne S., and Edgar Dale. *Readability Revisited: The New Dale-Chall Readability Formula.* Brookline Books, 1995.

### How to Achieve the Target Reading Level

When drafting the response, apply the following plain language techniques to keep the reading level within the 6th–8th grade range:

#### Sentence Length
- **Target average sentence length of 15 to 20 words.** Sentences over 25 words should be split into two shorter sentences.
- Vary sentence length for natural rhythm, but avoid consecutive long sentences.
- ❌ *"Our records show that, on February 26, 2026, a Cash App specialist reached out to you via email to notify you that, based on the information you provided, Cash App determined the activity you reported was unauthorized, and your account received a credit totaling $996.19 on that same date."* (50 words)
- ✅ Split into: *"On February 26, 2026, a Cash App specialist reached out to you via email. Cash App determined the activity you reported was unauthorized. Cash App issued a credit of $996.19 to your account on that same date."* (three sentences averaging 13 words)

#### Word Choice
- **Use common, everyday words.** Replace complex or technical words with simpler alternatives wherever possible without losing precision.

| Instead of | Use |
|------------|-----|
| "subsequently" | "then" or "after that" |
| "pursuant to" | "under" or "based on" |
| "in conjunction with" | "along with" or "with" |
| "notwithstanding" | "despite" or "even though" |
| "aforementioned" | "this" or "the" (with specific reference) |
| "commence" | "start" or "begin" |
| "terminate" | "close" or "end" |
| "reimburse" | "refund" or "pay back" (use "reimburse" only with footnote if needed) |
| "initiate" | "start" or "file" |
| "facilitate" | "help" or "provide" |
| "utilize" | "use" |
| "in the amount of" | "for" or "totaling" |
| "at this time" | "now" |
| "prior to" | "before" |

- **Exception:** Legal and financial terms that are required for precision (e.g., "Terms of Service," "peer-to-peer payment," "Cash Out," "dispute") should be retained but must be explained via footnotes on first use.

#### Paragraph Structure
- **Keep paragraphs to three to five sentences.** Break long paragraphs into shorter ones.
- **Lead with the main point.** Place the most important information at the beginning of each paragraph.
- **One idea per paragraph.** Do not combine multiple topics in a single paragraph.

#### Readability Verification

After drafting the response, perform a readability check:

1. **Count the total words, sentences, and syllables** in the response body (Sections II, III, and IV — exclude the header, salutation, and closing).
2. **Calculate the Flesch-Kincaid Grade Level** using the formula above.
3. **If the score exceeds 8.0:**
   - Identify sentences over 25 words and split them.
   - Replace complex words with simpler alternatives from the word choice table.
   - Reduce the number of multi-syllable words where possible.
   - Recalculate until the score falls within the 6.0–8.0 range.
4. **Report the readability score** in the Handler Review Notes table as follows:

| Metric | Value | Target |
|--------|-------|--------|
| Flesch-Kincaid Grade Level | [calculated score] | 6.0–8.0 |
| Average sentence length | [words per sentence] | 15–20 |
| Status | [✅ Within target / ⚠️ Above target — revisions applied] | |

### Balancing Readability with Legal Precision

Some legal and financial terms cannot be simplified without losing necessary precision. In these cases:
- **Retain the precise term** but explain it in a footnote on first use.
- **Do not sacrifice accuracy for readability.** If a sentence must use a complex term, keep the surrounding sentence structure simple.
- **The standard boilerplate in Section I is exempt** from readability optimization — it must remain verbatim.
- **Customer names, addresses, complaint numbers, and transaction details** are exempt from word-choice simplification.

## Important Reminders

- **Never fabricate facts.** If information is not in the investigation notes, flag it with `[HANDLER: please provide...]` rather than guessing.
- **Never include internal links or system references** in the response letter.
- **PII-gated responses:** If PII is NOT VERIFIED, the response cannot include account-specific details. Use the SR IDV/PII Mismatch template approach instead, or flag for the handler.
- **Duplicate complaints:** If the TL;DR mentions this is a duplicate, use the Duplicate Complaint template and reference the prior response.
- **Escalation guidance:** If the investigation notes reference specific SME or lead guidance (e.g., "per leads approval", "SME denied sharing detailed information"), follow that guidance in the response.

## Handler Post-Draft Checklist

After the draft is presented, the handler should verify:

- [ ] Template selection was correct (if auto-selected, confirm the choice)
- [ ] All facts match the investigation notes
- [ ] Customer's full name and mailing address are correct
- [ ] Response aligns with any SME/lead guidance from escalations
- [ ] Document uses **Montserrat font, Normal weight, 11pt** (body) and **10pt** (footnotes)
- [ ] All `[HANDLER: ...]` markers have been resolved
- [ ] Readability score is within the 6.0–8.0 target range
- [ ] Optionally, run the `ccot-compliance-reviewer` skill for a Legal and Compliance risk review
- [ ] Save the final version to the complaint's Google Drive folder as a PDF
- [ ] Add a "Response sent [date]" comment to the JIRA with a link to the Google Drive file

---

## Step 4: Present the Draft

1. Present the complete draft response to the handler.
2. Show which template was used and how it was selected (auto-selected or handler-provided).
3. Flag any areas where information was missing or unclear from the investigation notes (use `[HANDLER: ...]` markers).
4. Flag if the PII was NOT VERIFIED — this affects whether the response can include account-specific details.
5. Note the customer's mailing address — this must be provided by the handler if not in the investigation notes (it comes from the complaint filing, not JIRA).
6. Present the readability score table.
7. After presenting the draft, remind the handler: "To run a Legal and Compliance risk review on this draft, use the `ccot-compliance-reviewer` skill."
