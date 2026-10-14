"""
SpamGuard AI — Interview Preparation Guide PDF Generator

Generates a publication-grade, professionally designed PDF guide
covering every technical, ML, architectural, and security question
an interviewer can ask about SpamGuard AI.
"""

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PDF = os.path.join(PROJECT_ROOT, "SpamGuard_AI_Interview_Preparation_Guide.pdf")


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page numbers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Header (pages after cover/first page)
        if self._pageNumber > 1:
            self.drawString(54, 750, "SpamGuard AI — Master Interview Preparation & Project Defense Guide")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)

        self.drawString(54, 32, "Confidential — Prepared for Technical & System Design Interviews")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom palette
    primary_color = colors.HexColor("#1E3A8A")  # Deep Navy
    secondary_color = colors.HexColor("#4F46E5")  # Indigo
    accent_color = colors.HexColor("#0D9488")  # Teal
    dark_slate = colors.HexColor("#0F172A")  # Almost black
    text_color = colors.HexColor("#334155")  # Charcoal
    bg_box = colors.HexColor("#F8FAFC")  # Very light gray-blue
    border_box = colors.HexColor("#E2E8F0")

    # Typography styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=primary_color,
        alignment=0,
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=accent_color,
        spaceAfter=15,
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    question_style = ParagraphStyle(
        "Question",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=secondary_color,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True,
    )

    why_ask_style = ParagraphStyle(
        "WhyAsk",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#475569"),
        spaceAfter=4,
    )

    answer_style = ParagraphStyle(
        "Answer",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12.5,
        textColor=text_color,
        spaceAfter=6,
    )

    cheat_header = ParagraphStyle(
        "CheatHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    )

    cheat_cell = ParagraphStyle(
        "CheatCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=dark_slate,
    )

    story = []

    # --- Title Banner ---
    story.append(Paragraph("SpamGuard AI — Interview Defense & Technical Mastery Guide", title_style))
    story.append(
        Paragraph("Complete Technical Q&A, Architecture Deep Dives, Real Metrics & Defense Strategies", subtitle_style)
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=12))

    # --- Executive Summary Box ---
    summary_text = (
        "<b>Project Quick Summary for Introductions:</b><br/>"
        "SpamGuard AI is an end-to-end, privacy-first email spam and phishing screening web application. "
        "It features a custom word-embedding neural network trained on the Apache SpamAssassin corpus and served via "
        "a zero-dependency pure-NumPy runtime that eliminates TensorFlow in production to fit within a strict 512MB RAM constraint. "
        "It combines ML classification with rule-based heuristics and a 3-class decision framework (Spam, Not Spam, Uncertain). "
        "It achieves <b>97.86% accuracy, 98.79% precision, and 0.9916 ROC-AUC</b> with a mathematical Parity Gate ensuring zero score deviation."
    )
    summary_table = Table(
        [[Paragraph(summary_text, answer_style)]],
        colWidths=[504],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg_box),
                ("BOX", (0, 0), (-1, -1), 1, border_box),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # --- Questions & Answers Data ---
    sections = [
        (
            "1. High-Level Architecture & System Design",
            [
                (
                    "Q1: Can you walk me through the end-to-end architecture of SpamGuard AI?",
                    "Testing holistic system understanding from client to ML runtime.",
                    "The system follows a clean 3-tier architecture: (1) Client Tier: Accessible, zero-dependency HTML5/CSS/ES6 frontend with strict CSP compliance (no inline scripts/styles). (2) Application Tier: Flask with Waitress (local Windows) or Gunicorn (Linux/Docker), using Flask-Limiter for rate limiting and Flask-Talisman for HTTP security headers. (3) Inference & Logic Tier: A singleton ModelService executing a custom pure-NumPy forward pass alongside a heuristic rule engine that flags urgency, credential harvesting, and deceptive URLs. Zero user email content is ever logged or persisted to disk.",
                ),
                (
                    "Q2: Why did you build this as a standalone web application instead of a simple Jupyter notebook or CLI?",
                    "Evaluates practical engineering mindset and real-world deployment focus.",
                    "In production ML, modeling is often less than 20% of the effort; the critical challenges lie in serving latency, memory footprints, input validation, security, and user experience. Building SpamGuard AI as a production service forced solving real systems engineering challenges: strict 512MB container memory budgets, zero-dependency deployment, cold-start mitigation, XSS prevention, and privacy enforcement.",
                ),
                (
                    "Q3: Why is there no database in the application?",
                    "Tests understanding of data governance, security risk, and product requirements.",
                    "SpamGuard AI was intentionally designed as a zero-persistence service for user privacy and compliance. Users frequently submit emails containing sensitive personal data, corporate communications, or financial notices. By keeping processing purely ephemeral in RAM and returning responses immediately, we eliminate data leak liabilities, GDPR/CCPA storage burdens, and database overhead.",
                ),
            ],
        ),
        (
            "2. Machine Learning Architecture & Pure-NumPy Serving",
            [
                (
                    "Q4: What exact model architecture did you choose and why?",
                    "Tests architectural trade-off analysis between capacity, latency, and resource constraints.",
                    "I designed an Embedding + GlobalAveragePooling1D + Dense neural network: (1) Input sequence: 256 token IDs, (2) Embedding layer: 10,000 vocabulary size with 32-dimensional embedding, (3) GlobalAveragePooling1D: averages token vectors across the sequence length, (4) Dense Hidden Layer: 32 units with ReLU activation, (5) Dense Output Layer: 1 unit with Sigmoid activation. This architecture provides high representational capacity for word semantics while keeping total parameters under 325,000 (~3.5MB uncompressed weights), enabling microsecond inference on CPU.",
                ),
                (
                    "Q5: Why did you eliminate TensorFlow from the production runtime?",
                    "Crucial systems question: memory optimization and dependency reduction.",
                    "TensorFlow CPU is over 450MB on disk and consumes 200MB+ of RAM simply importing the library. Our production hosting target (Render Free Tier) provides a strict 512MB RAM budget. If Gunicorn runs with multiple worker threads, TensorFlow easily triggers Out-Of-Memory (OOM) kills. By extracting the trained weights (embedding table, dense kernels, and biases) into NumPy arrays, we implemented the entire forward pass in pure NumPy. NumPy loads in ~5ms, uses under 30MB of RAM, and runs single-prediction inference in under 2ms.",
                ),
                (
                    "Q6: What is the Parity Gate, and what were the exact verification results?",
                    "Tests rigorous ML testing standards and verification methodology.",
                    "A Parity Gate ensures that an optimized inference engine produces outputs mathematically identical to the development model. In our pipeline, ml/parity.py runs the entire held-out test set (889 emails) through both the reference model and the pure-NumPy runtime. The gate criteria required maximum absolute score difference < 1e-4 and zero label flips. Our real verified results: Max absolute difference = 8.62e-08, Mean absolute difference = 9.64e-09, Label mismatches = 0 (documented in docs/PARITY.md).",
                ),
            ],
        ),
        (
            "3. Data Engineering, Tokenization & Preprocessing",
            [
                (
                    "Q7: What dataset did you use, and how did you prevent data leakage?",
                    "Evaluates data preprocessing hygiene and train/val/test splitting rigor.",
                    "We used the Apache SpamAssassin Public Corpus (easy_ham, easy_ham_2, hard_ham, spam, spam_2). We parsed 6,047 raw RFC-822 MIME emails, stripped HTML tags with BeautifulSoup, and normalized whitespace. To prevent leakage: (1) Exact duplicates were removed using SHA-256 text hashing (126 duplicates removed). (2) Near-duplicates were clustered using 4-gram Jaccard similarity (threshold 0.85); near-duplicate clusters were assigned to the same split so identical templates never leak between train and test. (3) Data was split 70% train (4,144), 15% validation (888), 15% test (889) with a fixed random seed (42).",
                ),
                (
                    "Q8: Why write a custom Tokenizer instead of using Hugging Face or Keras TextVectorization?",
                    "Tests awareness of training-serving skew.",
                    "If training uses one tokenizer library (e.g., Keras TextVectorization) and production uses another, differences in regex handling, lowercase casing, or punctuation stripping cause training-serving skew. We wrote a single, self-contained Python/NumPy Tokenizer module (ml/tokenizer.py) that serializes its vocabulary to vocab.json. The exact same code runs during training, test evaluation, and production serving, guaranteeing 100% preprocessing consistency.",
                ),
            ],
        ),
        (
            "4. Evaluation Metrics, Decision Thresholds & Business Impact",
            [
                (
                    "Q9: What were the exact test set metrics, and why is Precision prioritized over Recall?",
                    "Tests real-world ML evaluation and business domain understanding.",
                    "On the 889 held-out test emails: Accuracy = 97.86%, Precision = 98.79%, Recall = 93.85%, F1 Score = 96.25%, ROC-AUC = 0.9916. Confusion Matrix: 626 True Negatives, 244 True Positives, 3 False Positives, 16 False Negatives. In spam filtering, a False Positive (classifying a critical job offer, flight ticket, or password reset as spam) is catastrophic to user trust, whereas a False Negative (a spam email reaching the inbox) is merely an inconvenience. Hence, precision must be prioritized.",
                ),
                (
                    "Q10: Why did you implement a 3-class system instead of a binary threshold at 0.5?",
                    "Demonstrates practical AI decision-making under uncertainty.",
                    "Standard binary classifiers force every prediction into 0 or 1, even when the model score is 0.51. In security, forced binary classification causes dangerous false certainty. We calibrated a 3-tier threshold system: Score >= 0.90 -> Confirmed Spam; Score <= 0.62 -> Not Spam; 0.62 < Score < 0.90 -> Uncertain. When an email falls into the Uncertain band, the UI advises the user to inspect sender identity, never click embedded links, and seek alternative verification.",
                ),
            ],
        ),
        (
            "5. Hybrid Detection: Machine Learning + Heuristic Rules",
            [
                (
                    "Q11: Why combine ML with heuristic rules? What are the limitations of an ML-only approach?",
                    "Evaluates depth in cybersecurity defense-in-depth strategies.",
                    "ML models detect learned statistical word distributions but are vulnerable to adversarial evasion (e.g., token stuffing, zero-width spaces, character substitution). Conversely, heuristics capture known signature patterns but fail on novel phrasing. By running both in parallel, SpamGuard AI provides defense-in-depth: the ML model scores text semantics, while the heuristic engine inspects structural signals like IP-based URLs (e.g. http://192.168.1.1), known URL shorteners, punycode/homograph domains, urgency cues, and credential theft keywords.",
                )
            ],
        ),
        (
            "6. Security Hardening, Privacy & Infrastructure",
            [
                (
                    "Q12: How did you verify that email content is NEVER logged?",
                    "Tests software testing rigor for privacy and compliance.",
                    "We enforced privacy by architectural design and verified it through automated tests. In app/routes.py, request logs record only timestamp, route, HTTP status, request ID, and latency—never request payload bodies. In tests/test_app.py, dedicated unit tests (test_no_body_content_in_logs and test_no_subject_content_in_logs) inject unique canary tokens (e.g., CANARY_SECRET_TOKEN_XYZ) into the subject and body, intercept all log streams, and assert that the token does not appear anywhere in logs.",
                ),
                (
                    "Q13: What security headers did you implement and why?",
                    "Tests web application security knowledge.",
                    "We used Flask-Talisman to enforce: (1) Content Security Policy (CSP): default-src 'self', blocking script injection and CDN hijacking. (2) Frame Ancestors: 'none', completely preventing clickjacking attacks. (3) X-Content-Type-Options: 'nosniff', preventing MIME-sniffing exploits. (4) Referrer-Policy: 'no-referrer', ensuring submitted URLs are not leaked in headers. (5) HSTS in production, enforcing TLS.",
                ),
                (
                    "Q14: How does the app handle cold starts and rate limiting on free-tier hosting?",
                    "Shows experience with serverless/PaaS operational constraints.",
                    "On Render's free tier, the container spins down after 15 minutes of inactivity. Cold start wake times can reach 50-60 seconds. To manage this: (1) ModelService performs an eager pre-warming inference dummy run during container boot so the first user request experiences zero JIT compilation lag. (2) Health endpoint (/api/health) exposes readiness. (3) Rate limiting via Flask-Limiter is configured at 20 requests/minute to defend against denial-of-service.",
                ),
            ],
        ),
        (
            "7. Quality Assurance, Edge Cases & Honest Limitations",
            [
                (
                    "Q15: How did you test edge cases like emojis, foreign scripts, and XSS injection?",
                    "Demonstrates defensive programming and robust QA practices.",
                    "In tests/test_app.py, we wrote explicit test suites for: (1) Unicode & Emojis: test_emoji_input_does_not_crash, verifying surrogate pairs don't break string parsing. (2) Right-to-Left (RTL) & Foreign Alphabets: Arabic and Chinese test cases verifying tokenization robustness. (3) XSS Script Injections: Submitting <script>alert(1)</script> strings to verify that templates and JSON responses render inputs purely as inert text (textContent in vanilla JS).",
                ),
                (
                    "Q16: What are the honest limitations of your model and dataset?",
                    "Tests maturity, scientific honesty, and lack of exaggeration.",
                    "I plainly acknowledge three key limitations: (1) Temporal Dataset Bias: The SpamAssassin corpus was gathered in 2002–2003. Modern threats like crypto scams, MFA fatigue phishing, and LLM-generated spear phishing are under-represented. (2) Content-Only Scope: The model evaluates text body and subject only; it does not inspect SPF/DKIM authentication, mail relay headers, or attachment binaries. (3) Language Limitation: The corpus is primarily English; accuracy on multilingual spam is not guaranteed.",
                ),
            ],
        ),
    ]

    for sec_title, qas in sections:
        story.append(Paragraph(sec_title, section_heading))
        story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#CBD5E1"), spaceAfter=6))

        for q, why, a in qas:
            q_flowables = [
                Paragraph(q, question_style),
                Paragraph(f"<b>What the interviewer is evaluating:</b> {why}", why_ask_style),
                Paragraph(a, answer_style),
                Spacer(1, 4),
            ]
            story.append(KeepTogether(q_flowables))

    # --- Section 8: Quick Reference Numbers to Memorize ---
    story.append(PageBreak())
    story.append(Paragraph("8. Key Numbers & Metrics Cheat Sheet (Memorize for Interviews)", section_heading))
    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=8))

    cheat_data = [
        [
            Paragraph("<b>Metric / Parameter</b>", cheat_header),
            Paragraph("<b>Value</b>", cheat_header),
            Paragraph("<b>Engineering Significance</b>", cheat_header),
        ],
        [
            Paragraph("Accuracy", cheat_cell),
            Paragraph("<b>97.86%</b>", cheat_cell),
            Paragraph("Evaluated on 889 held-out test emails never seen during training.", cheat_cell),
        ],
        [
            Paragraph("Precision", cheat_cell),
            Paragraph("<b>98.79%</b>", cheat_cell),
            Paragraph("Critical metric: Only 3 legitimate emails out of 629 were falsely flagged.", cheat_cell),
        ],
        [
            Paragraph("Recall", cheat_cell),
            Paragraph("<b>93.85%</b>", cheat_cell),
            Paragraph("244 out of 260 spam emails correctly intercepted.", cheat_cell),
        ],
        [
            Paragraph("ROC-AUC", cheat_cell),
            Paragraph("<b>0.9916</b>", cheat_cell),
            Paragraph("Demonstrates exceptional discriminative capability across all thresholds.", cheat_cell),
        ],
        [
            Paragraph("Parity Gate Max Diff", cheat_cell),
            Paragraph("<b>8.62e-08</b>", cheat_cell),
            Paragraph(
                "Proven numerical equivalence between Keras training and NumPy runtime (tolerance 1e-4).", cheat_cell
            ),
        ],
        [
            Paragraph("Decision Thresholds", cheat_cell),
            Paragraph("Spam &gt;= 0.90<br/>Ham &lt;= 0.62", cheat_cell),
            Paragraph(
                "Calibrated 3-class boundary; 0.62–0.90 is classified as 'Uncertain' to avoid false certainty.",
                cheat_cell,
            ),
        ],
        [
            Paragraph("Dataset Size", cheat_cell),
            Paragraph("<b>5,921 emails</b>", cheat_cell),
            Paragraph("Deduplicated from 6,047 raw files (4,047 Ham / 1,874 Spam). Split: 70/15/15.", cheat_cell),
        ],
        [
            Paragraph("Vocabulary & Seq Length", cheat_cell),
            Paragraph("10,000 vocab / 256 len", cheat_cell),
            Paragraph("Embedding dim = 32. Total parameters = ~325,000 (~3.5MB uncompressed).", cheat_cell),
        ],
        [
            Paragraph("Serving Memory Footprint", cheat_cell),
            Paragraph("<b>&lt; 35 MB RAM</b>", cheat_cell),
            Paragraph("Pure NumPy forward pass allows effortless execution within 512MB hosting limit.", cheat_cell),
        ],
        [
            Paragraph("Test Suite Pass Rate", cheat_cell),
            Paragraph("<b>41 / 41 Tests Passed</b>", cheat_cell),
            Paragraph("100% pytest pass rate in 1.1s; 17/17 smoke test checks passed.", cheat_cell),
        ],
    ]

    cheat_table = Table(cheat_data, colWidths=[120, 110, 274])
    cheat_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), primary_color),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_box]),
                ("GRID", (0, 0), (-1, -1), 0.5, border_box),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(cheat_table)
    story.append(Spacer(1, 14))

    # --- 30-Second Elevator Pitch Section ---
    pitch_box = [
        Paragraph("<b>The Perfect 60-Second Interview Elevator Pitch:</b>", question_style),
        Paragraph(
            '<i>"I built SpamGuard AI, a full-stack, privacy-first email spam and phishing screening system. '
            "Rather than just training a model in a notebook, I engineered the entire production pipeline to operate under strict real-world constraints: "
            "a 512MB RAM free-tier budget and zero user data logging. "
            "To achieve this, I trained an Embedding and GlobalAveragePooling network in Keras, and then exported the weights into a custom, pure-NumPy "
            "inference runtime that completely removes TensorFlow from production, reducing memory by 85% and achieving microsecond latency. "
            "I instituted a mathematical Parity Gate verifying that NumPy matches the reference model within 8.62e-08 on all 889 test emails. "
            "I combined ML with a heuristic rule engine for detecting punycode, raw IP URLs, and urgency cues, using a 3-class decision framework. "
            "On the held-out test set, the system achieved 97.86% accuracy, 98.79% precision, and 0.9916 ROC-AUC. "
            'The backend is built with Flask, hardened with CSP and rate limiting, and backed by 41 passing automated tests and Docker CI/CD."</i>',
            answer_style,
        ),
    ]
    pitch_table = Table([[pitch_box]], colWidths=[504])
    pitch_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#BFDBFE")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(KeepTogether(pitch_table))

    # Build the PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF generated successfully at: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_pdf()
