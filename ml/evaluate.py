"""
SpamGuard AI — Model Evaluation

Standalone script to evaluate the saved model on the test set
and generate/update model_card.md.

Usage: python ml/evaluate.py
"""

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def generate_model_card(model_dir: str, metrics: dict) -> None:
    """Generate model_card.md from metrics.json."""
    prod = metrics.get("production_model", {})
    baseline = metrics.get("baseline", {})
    thresholds = metrics.get("thresholds", {})

    card_path = os.path.join(model_dir, "model_card.md")

    with open(card_path, "w", encoding="utf-8") as f:
        f.write("# Model Card — SpamGuard AI v1\n\n")

        f.write("## Model Details\n\n")
        f.write("- **Architecture:** Embedding + GlobalAveragePooling1D + Dense (ReLU) + Dense (Sigmoid)\n")
        f.write("- **Framework (training):** TensorFlow/Keras\n")
        f.write("- **Framework (serving):** NumPy-only forward pass\n")
        f.write(f"- **Version:** {metrics.get('model_version', 'v1')}\n")
        f.write(f"- **Dataset:** {metrics.get('dataset', 'Apache SpamAssassin Public Corpus')}\n\n")

        f.write("## Intended Use\n\n")
        f.write("- **Primary use:** Informational analysis of email text for spam indicators\n")
        f.write("- **Users:** Students, job seekers, office workers, everyday email users\n")
        f.write("- **Out of scope:** Enterprise email security, header/attachment analysis, legal evidence\n\n")

        f.write("## Test Set Metrics\n\n")
        f.write(
            "All metrics are from evaluation on a held-out test set never used during training or threshold selection.\n\n"
        )
        f.write("| Metric | Value |\n")
        f.write("|--------|-------|\n")
        f.write(
            f"| Accuracy | {prod.get('accuracy', 'N/A'):.4f} |\n"
            if isinstance(prod.get("accuracy"), (int, float))
            else "| Accuracy | N/A |\n"
        )
        f.write(
            f"| Precision | {prod.get('precision', 'N/A'):.4f} |\n"
            if isinstance(prod.get("precision"), (int, float))
            else "| Precision | N/A |\n"
        )
        f.write(
            f"| Recall | {prod.get('recall', 'N/A'):.4f} |\n"
            if isinstance(prod.get("recall"), (int, float))
            else "| Recall | N/A |\n"
        )
        f.write(
            f"| F1 Score | {prod.get('f1', 'N/A'):.4f} |\n"
            if isinstance(prod.get("f1"), (int, float))
            else "| F1 Score | N/A |\n"
        )
        f.write(
            f"| ROC-AUC | {prod.get('roc_auc', 'N/A'):.4f} |\n"
            if isinstance(prod.get("roc_auc"), (int, float))
            else "| ROC-AUC | N/A |\n"
        )
        f.write(f"| False Positives | {prod.get('fp_count', 'N/A')} |\n")
        f.write(f"| False Negatives | {prod.get('fn_count', 'N/A')} |\n\n")

        if baseline:
            f.write("## Baseline Comparison (TF-IDF + Logistic Regression)\n\n")
            f.write("| Metric | Baseline | Production Model |\n")
            f.write("|--------|----------|------------------|\n")
            for metric in ["accuracy", "precision", "recall", "f1", "roc_auc"]:
                b_val = baseline.get(metric, "N/A")
                p_val = prod.get(metric, "N/A")
                b_str = f"{b_val:.4f}" if isinstance(b_val, (int, float)) else str(b_val)
                p_str = f"{p_val:.4f}" if isinstance(p_val, (int, float)) else str(p_val)
                f.write(f"| {metric} | {b_str} | {p_str} |\n")
            f.write("\n")

        f.write("## Thresholds\n\n")
        f.write(f"- Spam threshold: {thresholds.get('spam_threshold', 'N/A')}\n")
        f.write(f"- Not-spam threshold: {thresholds.get('not_spam_threshold', 'N/A')}\n")
        f.write(f"- Mid threshold: {thresholds.get('mid_threshold', 'N/A')}\n\n")

        f.write("## Limitations\n\n")
        f.write("1. Trained on Apache SpamAssassin corpus (early 2000s). May not recognize modern phishing.\n")
        f.write("2. Analyzes text only — not headers, attachments, SPF/DKIM/DMARC, or sender reputation.\n")
        f.write("3. Model score is not a calibrated probability.\n")
        f.write("4. Does not guarantee an email is safe or malicious.\n")
        f.write("5. English-centric training data; may underperform on non-English text.\n\n")

        f.write("## Ethical Considerations\n\n")
        f.write("- No user data is stored or logged\n")
        f.write("- The tool should not be used as the sole basis for email security decisions\n")
        f.write("- False positives may cause legitimate emails to be ignored\n")
        f.write("- False negatives may cause users to trust malicious emails\n")

    print(f"Model card written to: {card_path}")


def main():
    model_dir = os.path.join(PROJECT_ROOT, "models", "v1")
    metrics_path = os.path.join(model_dir, "metrics.json")

    if not os.path.isfile(metrics_path):
        print(f"ERROR: metrics.json not found at {metrics_path}")
        print("Run ml/train.py first.")
        return 1

    with open(metrics_path) as f:
        metrics = json.load(f)

    generate_model_card(model_dir, metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
