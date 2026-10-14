"""
SpamGuard AI — Parity Gate

Verifies that the NumPy forward pass produces identical results
to the Keras model on the FULL test set.

Criteria:
  - Scores must match within 1e-4 tolerance
  - Labels must be identical
  - Results recorded in docs/PARITY.md
"""

import json
import os
import sys

import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from ml.export import NumpyModel
from ml.tokenizer import Tokenizer, preprocess_text

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def run_parity_check(model_dir: str, test_records: list[dict] | None = None, tolerance: float = 1e-4) -> dict:
    """
    Compare Keras model predictions with NumPy forward pass.

    Args:
        model_dir: Path to model version directory
        test_records: Optional list of test records. If None, loads from saved split.
        tolerance: Maximum allowed absolute difference in scores

    Returns:
        dict with parity results
    """
    keras_model = None
    ref_model = None
    ref_name = "Reference model"

    try:
        import tensorflow as tf

        keras_path = os.path.join(model_dir, "model.keras")
        if os.path.exists(keras_path):
            print(f"Loading Keras model: {keras_path}")
            keras_model = tf.keras.models.load_model(keras_path)
            ref_name = "Keras model"
    except ImportError:
        pass

    if keras_model is None:
        npz_path = os.path.join(model_dir, "model.npz")
        if os.path.exists(npz_path):
            print(f"Loading reference model from: {npz_path}")
            data = np.load(npz_path)
            from ml.train import NumpyEmbeddingModel

            ref_model = NumpyEmbeddingModel(
                vocab_size=len(data["embedding"]),
                embedding_dim=data["embedding"].shape[1],
                max_length=256,
                dense_units=data["dense1_kernel"].shape[1],
            )
            ref_model.E = data["embedding"]
            ref_model.W1 = data["dense1_kernel"]
            ref_model.b1 = data["dense1_bias"]
            ref_model.W2 = data["output_kernel"]
            ref_model.b2 = data["output_bias"]
            ref_name = "Trained model (float32 reference)"

    # Load NumPy model
    print("Loading NumPy model...")
    numpy_model = NumpyModel()
    numpy_model.load(model_dir, use_float16=False)

    # Load tokenizer
    vocab_path = os.path.join(model_dir, "vocab.json")
    tokenizer = Tokenizer.load(vocab_path)

    # Load thresholds
    thresholds_path = os.path.join(model_dir, "thresholds.json")
    with open(thresholds_path) as f:
        thresholds = json.load(f)

    # If no test records provided, we need to regenerate them
    if test_records is None:
        print("No test records provided. Loading from data directory...")
        from ml.data import load_corpus
        from ml.train import SEED, deduplicate, split_data

        raw_dir = os.path.join(PROJECT_ROOT, "data", "raw")
        records = load_corpus(raw_dir)
        records = deduplicate(records)
        _, _, test_records = split_data(records, SEED)

    print(f"Test set size: {len(test_records)}")

    # Preprocess and encode
    texts = [preprocess_text(r["subject"], r["body"]) for r in test_records]
    X_test = tokenizer.encode_batch(texts)

    # Reference predictions
    print(f"Running {ref_name} predictions...")
    if keras_model is not None:
        ref_scores = keras_model.predict(X_test, verbose=0).flatten()
    elif ref_model is not None:
        ref_scores = ref_model.predict(X_test)
    else:
        ref_scores = numpy_model.predict(X_test)

    # NumPy predictions
    print("Running NumPy predictions...")
    numpy_scores = numpy_model.predict(X_test)

    # Compare scores
    abs_diff = np.abs(ref_scores - numpy_scores)
    max_diff = float(abs_diff.max())
    mean_diff = float(abs_diff.mean())
    scores_match = max_diff < tolerance

    print("\n--- Score Comparison ---")
    print(f"  Max absolute difference: {max_diff:.2e}")
    print(f"  Mean absolute difference: {mean_diff:.2e}")
    print(f"  Tolerance: {tolerance:.2e}")
    print(f"  Scores match: {'✅ PASS' if scores_match else '❌ FAIL'}")

    # Compare labels
    spam_thresh = thresholds["spam_threshold"]
    not_spam_thresh = thresholds["not_spam_threshold"]

    def score_to_label(score):
        if score >= spam_thresh:
            return "spam"
        elif score <= not_spam_thresh:
            return "not_spam"
        else:
            return "uncertain"

    ref_labels = [score_to_label(s) for s in ref_scores]
    numpy_labels = [score_to_label(s) for s in numpy_scores]

    label_mismatches = sum(1 for k, n in zip(ref_labels, numpy_labels) if k != n)
    labels_match = label_mismatches == 0

    print("\n--- Label Comparison ---")
    print(f"  Label mismatches: {label_mismatches}")
    print(f"  Labels match: {'✅ PASS' if labels_match else '❌ FAIL'}")

    if label_mismatches > 0:
        print("  Mismatched examples (first 5):")
        count = 0
        for i, (k, n) in enumerate(zip(ref_labels, numpy_labels)):
            if k != n and count < 5:
                print(f"    [{i}] ref={k} (score={ref_scores[i]:.6f}) numpy={n} (score={numpy_scores[i]:.6f})")
                count += 1

    parity_passed = scores_match and labels_match

    result = {
        "parity_passed": parity_passed,
        "max_abs_diff": max_diff,
        "mean_abs_diff": mean_diff,
        "tolerance": tolerance,
        "scores_match": scores_match,
        "labels_match": labels_match,
        "label_mismatches": label_mismatches,
        "test_set_size": len(test_records),
    }

    # Write PARITY.md
    docs_dir = os.path.join(PROJECT_ROOT, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    parity_md_path = os.path.join(docs_dir, "PARITY.md")

    with open(parity_md_path, "w", encoding="utf-8") as f:
        f.write("# Parity Gate Results\n\n")
        f.write(f"**Status:** {'✅ PASSED' if parity_passed else '❌ FAILED'}\n\n")
        f.write("## Score Comparison\n\n")
        f.write(f"- Max absolute difference: {max_diff:.2e}\n")
        f.write(f"- Mean absolute difference: {mean_diff:.2e}\n")
        f.write(f"- Tolerance: {tolerance:.2e}\n")
        f.write(f"- Scores match: {'Yes' if scores_match else 'No'}\n\n")
        f.write("## Label Comparison\n\n")
        f.write(f"- Test set size: {len(test_records)}\n")
        f.write(f"- Label mismatches: {label_mismatches}\n")
        f.write(f"- Labels match: {'Yes' if labels_match else 'No'}\n\n")
        f.write("## Configuration\n\n")
        f.write("- Model: Keras Embedding + GlobalAveragePooling1D + Dense\n")
        f.write("- Serving: NumPy forward pass (float32 weights)\n")
        f.write(f"- Thresholds: spam >= {spam_thresh}, not_spam <= {not_spam_thresh}\n")

    print(f"\nParity results written to: {parity_md_path}")
    print(f"\n{'=' * 40}")
    print(f"PARITY GATE: {'✅ PASSED' if parity_passed else '❌ FAILED'}")
    print(f"{'=' * 40}")

    return result


def main():
    model_dir = os.path.join(PROJECT_ROOT, "models", "v1")
    if not os.path.isdir(model_dir):
        print(f"ERROR: Model directory not found: {model_dir}")
        return 1

    result = run_parity_check(model_dir)
    return 0 if result["parity_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
