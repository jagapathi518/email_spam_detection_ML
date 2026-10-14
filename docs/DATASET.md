# Dataset Documentation

## Primary Source: Apache SpamAssassin Public Corpus

**URL:** https://spamassassin.apache.org/old/publiccorpus/

**License:** The Apache SpamAssassin Public Corpus is freely available for research and educational use. Individual emails within the corpus may have varied original licenses from their senders. The corpus has been widely used in academic research since its release.

**Files Used:**
| File | Label | Description |
|------|-------|-------------|
| 20030228_easy_ham.tar.bz2 | ham | Easy-to-classify legitimate emails |
| 20030228_easy_ham_2.tar.bz2 | ham | Second batch of easy legitimate emails |
| 20030228_hard_ham.tar.bz2 | ham | Harder-to-classify legitimate emails |
| 20030228_spam.tar.bz2 | spam | Spam emails |
| 20030228_spam_2.tar.bz2 | spam | Second batch of spam emails |

## Known Biases and Limitations

1. **Corpus Age:** The emails were collected around 2002–2003. Modern phishing techniques (e.g., spear phishing with personalization, COVID-19 scams, cryptocurrency scams, AI-generated text) are not represented.

2. **Email Composition:** The corpus primarily contains English-language emails. Non-English spam and phishing may not be detected well.

3. **Under-Representation of Modern Phishing:** The corpus predates social media, cloud services, and modern SaaS platforms. Phishing emails impersonating these services are absent.

4. **Class Imbalance:** The corpus has approximately 2:1 ratio of ham to spam. This reflects real-world distributions to some extent but may vary from current email volumes.

5. **Limited Header/Attachment Analysis:** This project uses only subject and body text. The corpus does contain full headers, but they are not used for prediction.

6. **Geographic and Demographic Bias:** The original email senders likely represent a narrow demographic (English-speaking tech users circa 2003).

## Data Processing

- Raw emails are parsed with Python's `email` module
- MIME multipart handling with charset detection
- HTML content stripped via BeautifulSoup
- Exact duplicates removed via SHA-256 hash of normalized text
- Near-duplicates detected via character 4-gram Jaccard similarity (threshold 0.85)
- Near-duplicates are kept in the same train/val/test split to prevent data leakage
- Split: 70% train / 15% validation / 15% test (fixed seed = 42)
- Test set used only once for final evaluation

## Alternative Data Sources Considered

- **Enron-Spam:** Another well-known corpus. Not used as primary because SpamAssassin is more widely cited and has clearer provenance.
- **Modern phishing datasets:** Several exist but many require registration, have restrictive licenses, or contain synthetic data. The gap in modern phishing coverage is documented as a limitation rather than addressed with unverified data.
