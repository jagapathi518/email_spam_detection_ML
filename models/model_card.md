# Model Card: SpamGuard AI (Version v1)

## Model Details
- **Model Name:** SpamGuard AI Text Classifier
- **Model Version:** v1
- **Architecture:** Word Tokenization (vocab size: 10,000, max sequence length: 256) -> Embedding (dim: 32) -> GlobalAveragePooling1D -> Dense (32 units, ReLU) -> Dense (1 unit, Sigmoid)
- **Framework:** Developed with Keras / Python, exported to NumPy float32 weights (`model.npz`) for zero-dependency, low-latency CPU production inference.
- **License:** Open Source (educational / research use).

## Intended Use
- **Primary Intended Use:** Rapid, privacy-respecting client/server screening of suspicious email subject lines and email body text for individual users (students, job seekers, everyday office workers).
- **Out-of-Scope Use:** Automated enterprise email deletion/filtering without human review, legal or forensic evidence collection, or safety assurance for critical infrastructure.

## Training & Evaluation Data
- **Dataset:** Apache SpamAssassin Public Corpus (2002–2003 release).
- **Preprocessing:** MIME multipart unwrapping, HTML body stripping, custom tokenization and sequence padding to 256 tokens.
- **Deduplication:** Exact SHA-256 deduplication and 4-gram Jaccard similarity near-duplicate clustering.
- **Dataset Size:** 5,921 clean deduplicated emails.
- **Data Split:** 70% Training / 15% Validation / 15% Test (fixed random seed = 42).

## Evaluation Metrics (Held-Out Test Set, N=889)
All metrics reflect performance on 889 held-out test emails (629 ham, 260 spam) never seen during training:
- **Accuracy:** 97.86% (0.9786)
- **Precision:** 98.79% (0.9879)
- **Recall:** 93.85% (0.9385)
- **F1 Score:** 96.25% (0.9625)
- **ROC-AUC:** 0.9916
- **Confusion Matrix:**
  - True Negatives (Ham correctly identified): 626
  - False Positives (Ham incorrectly flagged as spam): 3
  - False Negatives (Spam missed): 16
  - True Positives (Spam correctly caught): 244

## Decision Thresholds
- **Spam Threshold:** Score >= 0.90
- **Not Spam Threshold:** Score <= 0.62
- **Uncertain Range:** 0.62 < Score < 0.90
- **False Positive Rate at Midpoint:** 0.16% (3 / 629)

## Serving Runtime & Parity Verification
- **Serving Engine:** Lightweight pure-NumPy inference pipeline (no TensorFlow in production runtime).
- **Parity Gate:** Full test-set verification confirms that NumPy output matches reference model scores within 8.62e-08 (tolerance: 1.00e-04) with 0 label mismatches across all 889 test emails.

## Limitations & Ethical Considerations
1. **Historical Dataset:** The SpamAssassin corpus was gathered in the early 2000s. Emerging modern attack vectors (e.g., cryptocurrency investment schemes, multi-factor authentication phishing, AI-synthesized spear phishing) are under-represented.
2. **Text-Only Scope:** Predictions evaluate only text syntax and content. Header authentication (SPF, DKIM, DMARC), email relay chains, domain reputation, and binary attachments are not inspected.
3. **Language Bias:** Data is overwhelmingly English; performance on non-English text cannot be guaranteed.
4. **No Absolute Safety Guarantee:** A "not spam" verdict does not certify an email is benign. Users must always verify sender credentials and never open unverified links or attachments.
