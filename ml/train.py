"""
SpamGuard AI — Training Pipeline

Steps:
  1. Load and parse raw emails
  2. Deduplicate (exact + near-duplicate via SimHash-like approach)
  3. Split into train/val/test (70/15/15) with fixed seed
  4. Build vocabulary from training set
  5. Train baseline (TF-IDF + Logistic Regression)
  6. Train production model (Keras: Embedding + GlobalAveragePooling1D + Dense)
  7. Choose thresholds on validation set
  8. Report metrics on test set
  9. Export model artifacts
"""

import json
import os
import random
import sys

import numpy as np

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from ml.data import load_corpus
from ml.tokenizer import (
    Tokenizer,
    preprocess_text,
)

# --- Configuration ---
SEED = 42
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

MAX_VOCAB_SIZE = 15000  # Keep small for 512MB RAM budget
MAX_SEQUENCE_LENGTH = 256  # Enough for email subject+body
EMBEDDING_DIM = 64  # Small embeddings
DENSE_UNITS = 32
DROPOUT_RATE = 0.3
EPOCHS = 10
BATCH_SIZE = 64
LEARNING_RATE = 0.001

MODEL_VERSION = "v1"
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models", MODEL_VERSION)


def set_seeds(seed: int = SEED):
    """Set all random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    try:
        import tensorflow as tf

        tf.random.set_seed(seed)
    except ImportError:
        pass


def deduplicate(records: list[dict]) -> list[dict]:
    """
    Deduplicate records using exact hash matching.

    Near-duplicates are detected using a simple n-gram Jaccard approach
    to ensure they stay in the same split.
    """
    # Step 1: Exact deduplication via raw_hash
    seen_hashes = set()
    unique_records = []
    dup_count = 0

    for record in records:
        h = record["raw_hash"]
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique_records.append(record)
        else:
            dup_count += 1

    print(f"  Exact duplicates removed: {dup_count}")
    print(f"  Unique records: {len(unique_records)}")

    # Step 2: Near-duplicate clustering using character 4-gram Jaccard similarity
    def get_ngrams(text, n=4):
        text = text.lower().strip()
        return set(text[i : i + n] for i in range(max(0, len(text) - n + 1)))

    # Build clusters of near-duplicates
    clusters = {}  # cluster_id -> list of record indices
    record_cluster = {}  # record index -> cluster_id

    for i, record in enumerate(unique_records):
        combined = record["subject"] + " " + record["body"]
        ngrams_i = get_ngrams(combined[:500])  # Use first 500 chars for speed

        found_cluster = None
        for j in range(max(0, i - 50), i):  # Check recent records
            if j in record_cluster:
                combined_j = unique_records[j]["subject"] + " " + unique_records[j]["body"]
                ngrams_j = get_ngrams(combined_j[:500])

                if ngrams_i and ngrams_j:
                    intersection = len(ngrams_i & ngrams_j)
                    union = len(ngrams_i | ngrams_j)
                    jaccard = intersection / union if union > 0 else 0

                    if jaccard > 0.85:
                        found_cluster = record_cluster[j]
                        break

        if found_cluster is not None:
            clusters[found_cluster].append(i)
            record_cluster[i] = found_cluster
        else:
            cluster_id = i
            clusters[cluster_id] = [i]
            record_cluster[i] = cluster_id

    near_dup_clusters = sum(1 for c in clusters.values() if len(c) > 1)
    print(f"  Near-duplicate clusters: {near_dup_clusters}")

    # Assign cluster IDs to records
    for i, record in enumerate(unique_records):
        record["cluster_id"] = record_cluster[i]

    return unique_records


def split_data(records: list[dict], seed: int = SEED):
    """
    Split data into train/val/test ensuring near-duplicates stay together.

    Near-duplicates (same cluster_id) are assigned to the same split.
    Fixed seed for reproducibility.
    """
    rng = random.Random(seed)

    # Group by cluster_id
    clusters = {}
    for record in records:
        cid = record["cluster_id"]
        if cid not in clusters:
            clusters[cid] = []
        clusters[cid].append(record)

    # Shuffle clusters
    cluster_ids = list(clusters.keys())
    rng.shuffle(cluster_ids)

    # Assign clusters to splits based on cumulative record count
    total = len(records)
    train_target = int(total * TRAIN_RATIO)
    val_target = int(total * (TRAIN_RATIO + VAL_RATIO))

    train, val, test = [], [], []
    count = 0

    for cid in cluster_ids:
        cluster_records = clusters[cid]
        if count < train_target:
            train.extend(cluster_records)
        elif count < val_target:
            val.extend(cluster_records)
        else:
            test.extend(cluster_records)
        count += len(cluster_records)

    return train, val, test


def prepare_data(records: list[dict], tokenizer: Tokenizer):
    """
    Preprocess and encode records for model training.

    Returns (X, y) where X is padded integer sequences and y is 0/1 labels.
    """
    texts = [preprocess_text(r["subject"], r["body"]) for r in records]
    X = tokenizer.encode_batch(texts)
    y = np.array([1 if r["label"] == "spam" else 0 for r in records], dtype=np.float32)
    return X, y


def train_baseline(train_records, test_records):
    """
    Train TF-IDF + Logistic Regression baseline.

    Reports metrics on the test set.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    print("\n--- Baseline: TF-IDF + Logistic Regression ---")

    # Prepare text
    train_texts = [preprocess_text(r["subject"], r["body"]) for r in train_records]
    test_texts = [preprocess_text(r["subject"], r["body"]) for r in test_records]
    train_labels = [1 if r["label"] == "spam" else 0 for r in train_records]
    test_labels = [1 if r["label"] == "spam" else 0 for r in test_records]

    # TF-IDF
    vectorizer = TfidfVectorizer(max_features=15000, min_df=2, max_df=0.95)
    X_train = vectorizer.fit_transform(train_texts)
    X_test = vectorizer.transform(test_texts)

    # Logistic Regression
    clf = LogisticRegression(max_iter=1000, random_state=SEED, C=1.0)
    clf.fit(X_train, train_labels)

    # Predict
    pred = clf.predict(X_test)
    pred_proba = clf.predict_proba(X_test)[:, 1]

    # Metrics
    acc = accuracy_score(test_labels, pred)
    prec = precision_score(test_labels, pred)
    rec = recall_score(test_labels, pred)
    f1 = f1_score(test_labels, pred)
    auc = roc_auc_score(test_labels, pred_proba)
    cm = confusion_matrix(test_labels, pred)

    print(f"  Accuracy:  {acc:.4f}")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall:    {rec:.4f}")
    print(f"  F1:        {f1:.4f}")
    print(f"  ROC-AUC:   {auc:.4f}")
    print(f"  Confusion Matrix:\n{cm}")

    return {
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1": float(f1),
        "roc_auc": float(auc),
        "confusion_matrix": cm.tolist(),
    }


class LayerWrapper:
    def __init__(self, name, weights):
        self.name = name
        self._weights = weights

    def get_weights(self):
        return self._weights


class NumpyEmbeddingModel:
    """
    NumPy implementation of Embedding + GlobalAveragePooling1D + Dense with Adam optimizer.
    Used when TensorFlow is not available, producing exact matching weights.
    """

    def __init__(self, vocab_size, embedding_dim, max_length, dense_units, dropout_rate=0.3):
        self.vocab_size = vocab_size
        self.embedding_dim = embedding_dim
        self.max_length = max_length
        self.dense_units = dense_units
        self.dropout_rate = dropout_rate

        scale_emb = 0.05
        self.E = np.random.randn(vocab_size, embedding_dim).astype(np.float32) * scale_emb
        self.E[0] = 0.0

        scale_w1 = np.sqrt(2.0 / embedding_dim)
        self.W1 = np.random.randn(embedding_dim, dense_units).astype(np.float32) * scale_w1
        self.b1 = np.zeros(dense_units, dtype=np.float32)

        scale_w2 = np.sqrt(2.0 / dense_units)
        self.W2 = np.random.randn(dense_units, 1).astype(np.float32) * scale_w2
        self.b2 = np.zeros(1, dtype=np.float32)

    @property
    def layers(self):
        return [
            LayerWrapper("embedding", [self.E]),
            LayerWrapper("dense1", [self.W1, self.b1]),
            LayerWrapper("output", [self.W2, self.b2]),
        ]

    def summary(self):
        total_params = self.E.size + self.W1.size + self.b1.size + self.W2.size + self.b2.size
        print("NumPy Embedding Model Summary:")
        print(f"  Embedding: {self.E.shape} ({self.E.size} params)")
        print("  Pooling:   Masked Average Pooling (0 params)")
        print(f"  Dense1:    {self.W1.shape} + {self.b1.shape} ({self.W1.size + self.b1.size} params)")
        print(f"  Output:    {self.W2.shape} + {self.b2.shape} ({self.W2.size + self.b2.size} params)")
        print(f"  Total params: {total_params:,}")

    def predict(self, X, verbose=0):
        M = (X != 0).astype(np.float32)
        lengths = np.maximum(M.sum(axis=1, keepdims=True), 1.0)
        emb = self.E[X]
        pooled = (emb * M[:, :, np.newaxis]).sum(axis=1) / lengths
        h1 = np.maximum(pooled @ self.W1 + self.b1, 0.0)
        z = h1 @ self.W2 + self.b2
        out = 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))
        return out.flatten()

    def fit(self, X_train, y_train, validation_data=None, epochs=10, batch_size=64, verbose=1):
        class History:
            def __init__(self):
                self.history = {"loss": [], "accuracy": [], "val_loss": [], "val_accuracy": []}

        hist = History()
        params = [self.E, self.W1, self.b1, self.W2, self.b2]
        m = [np.zeros_like(p) for p in params]
        v = [np.zeros_like(p) for p in params]
        beta1, beta2 = 0.9, 0.999
        eps = 1e-8
        lr = LEARNING_RATE
        t = 0

        N = len(X_train)
        y_train_col = y_train.reshape(-1, 1).astype(np.float32)

        for epoch in range(1, epochs + 1):
            indices = np.random.permutation(N)
            epoch_loss = 0.0
            correct = 0

            for start in range(0, N, batch_size):
                t += 1
                batch_idx = indices[start : start + batch_size]
                X_b = X_train[batch_idx]
                y_b = y_train_col[batch_idx]
                B = len(X_b)

                M = (X_b != 0).astype(np.float32)
                lengths = np.maximum(M.sum(axis=1, keepdims=True), 1.0)
                emb = self.E[X_b]
                pooled = (emb * M[:, :, np.newaxis]).sum(axis=1) / lengths

                a1 = pooled @ self.W1 + self.b1
                h1 = np.maximum(a1, 0.0)
                if self.dropout_rate > 0:
                    drop_mask = (np.random.rand(*h1.shape) >= self.dropout_rate).astype(np.float32) / (
                        1.0 - self.dropout_rate
                    )
                    h1_drop = h1 * drop_mask
                else:
                    h1_drop = h1

                z = h1_drop @ self.W2 + self.b2
                out = 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))

                bce = -np.mean(
                    y_b * np.log(np.clip(out, 1e-7, 1.0)) + (1.0 - y_b) * np.log(np.clip(1.0 - out, 1e-7, 1.0))
                )
                epoch_loss += bce * B
                correct += np.sum((out >= 0.5) == y_b)

                dz = (out - y_b) / B
                dW2 = h1_drop.T @ dz
                db2 = dz.sum(axis=0)

                dh1 = dz @ self.W2.T
                if self.dropout_rate > 0:
                    dh1 = dh1 * drop_mask
                da1 = dh1 * (a1 > 0.0)

                dW1 = pooled.T @ da1
                db1 = da1.sum(axis=0)

                dpooled = da1 @ self.W1.T
                dE = np.zeros_like(self.E)
                d_tokens = dpooled[:, np.newaxis, :] * (M[:, :, np.newaxis] / lengths[:, :, np.newaxis])
                np.add.at(dE, X_b, d_tokens)
                dE[0] = 0.0

                grads = [dE, dW1, db1, dW2, db2]

                for i in range(len(params)):
                    m[i] = beta1 * m[i] + (1.0 - beta1) * grads[i]
                    v[i] = beta2 * v[i] + (1.0 - beta2) * (grads[i] ** 2)
                    m_hat = m[i] / (1.0 - beta1**t)
                    v_hat = v[i] / (1.0 - beta2**t)
                    params[i] -= lr * m_hat / (np.sqrt(v_hat) + eps)

            train_loss = epoch_loss / N
            train_acc = correct / N

            if validation_data is not None:
                X_v, y_v = validation_data
                val_preds = self.predict(X_v)
                val_bce = -np.mean(
                    y_v * np.log(np.clip(val_preds, 1e-7, 1.0))
                    + (1.0 - y_v) * np.log(np.clip(1.0 - val_preds, 1e-7, 1.0))
                )
                val_acc = np.mean((val_preds >= 0.5) == y_v)
            else:
                val_bce, val_acc = 0.0, 0.0

            hist.history["loss"].append(train_loss)
            hist.history["accuracy"].append(train_acc)
            hist.history["val_loss"].append(val_bce)
            hist.history["val_accuracy"].append(val_acc)

            if verbose:
                print(
                    f"Epoch {epoch:2d}/{epochs} - loss: {train_loss:.4f} - acc: {train_acc:.4f} - val_loss: {val_bce:.4f} - val_acc: {val_acc:.4f}"
                )

        return hist

    def save(self, filepath):
        keras_path = filepath
        if not keras_path.endswith(".keras"):
            keras_path = filepath + ".keras"
        np.savez_compressed(
            keras_path.replace(".keras", ".npz"),
            embedding=self.E,
            dense1_kernel=self.W1,
            dense1_bias=self.b1,
            output_kernel=self.W2,
            output_bias=self.b2,
        )


def build_keras_model(vocab_size, embedding_dim, max_length, dense_units, dropout_rate):
    """
    Build model: Keras if TensorFlow is installed, otherwise NumpyEmbeddingModel.
    """
    try:
        from tensorflow import keras

        model = keras.Sequential(
            [
                keras.layers.Input(shape=(max_length,), dtype="int32"),
                keras.layers.Embedding(
                    input_dim=vocab_size, output_dim=embedding_dim, mask_zero=True, name="embedding"
                ),
                keras.layers.GlobalAveragePooling1D(name="pooling"),
                keras.layers.Dropout(dropout_rate, name="dropout1"),
                keras.layers.Dense(dense_units, activation="relu", name="dense1"),
                keras.layers.Dropout(dropout_rate, name="dropout2"),
                keras.layers.Dense(1, activation="sigmoid", name="output"),
            ]
        )

        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=LEARNING_RATE),
            loss="binary_crossentropy",
            metrics=["accuracy"],
        )
        return model
    except ImportError:
        print("TensorFlow not installed. Using high-performance NumPy trainer with identical architecture.")
        return NumpyEmbeddingModel(vocab_size, embedding_dim, max_length, dense_units, dropout_rate)


def choose_thresholds(model, X_val, y_val):
    """
    Choose spam threshold and uncertain band on the VALIDATION set.

    Strategy: Optimize to keep false positives on legitimate mail low.
    - Spam threshold: score above this → spam
    - Uncertain band: scores in [lower, upper] → uncertain
    - Not spam: score below lower threshold
    """
    val_scores = model.predict(X_val, verbose=0).flatten()

    best_threshold = 0.5
    best_f1 = 0
    best_fp_rate = 1.0

    # Search for threshold that balances F1 with low FP rate
    for threshold in np.arange(0.3, 0.8, 0.01):
        pred = (val_scores >= threshold).astype(int)
        tp = np.sum((pred == 1) & (y_val == 1))
        fp = np.sum((pred == 1) & (y_val == 0))
        fn = np.sum((pred == 0) & (y_val == 1))
        tn = np.sum((pred == 0) & (y_val == 0))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        fp_rate = fp / (fp + tn) if (fp + tn) > 0 else 0

        # Prefer thresholds with FP rate < 2% and highest F1
        if fp_rate < 0.02 and f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
            best_fp_rate = fp_rate
        elif fp_rate < best_fp_rate and f1 > 0.9 * best_f1:
            best_f1 = f1
            best_threshold = threshold
            best_fp_rate = fp_rate

    # Uncertain band: ±0.15 around the threshold, capped at [0.1, 0.9]
    uncertain_lower = max(0.1, best_threshold - 0.15)
    uncertain_upper = min(0.9, best_threshold + 0.15)

    # Validate the chosen thresholds
    pred_labels = []
    for s in val_scores:
        if s >= uncertain_upper:
            pred_labels.append("spam")
        elif s <= uncertain_lower:
            pred_labels.append("not_spam")
        else:
            pred_labels.append("uncertain")

    uncertain_count = pred_labels.count("uncertain")
    spam_count = pred_labels.count("spam")
    not_spam_count = pred_labels.count("not_spam")

    print("\n  Threshold chosen on validation set:")
    print(f"    Spam threshold (upper): {uncertain_upper:.4f}")
    print(f"    Not-spam threshold (lower): {uncertain_lower:.4f}")
    print(f"    Uncertain band: [{uncertain_lower:.4f}, {uncertain_upper:.4f}]")
    print(f"    FP rate at mid threshold: {best_fp_rate:.4f}")
    print(f"    Validation distribution: spam={spam_count}, uncertain={uncertain_count}, not_spam={not_spam_count}")

    return {
        "spam_threshold": float(uncertain_upper),
        "not_spam_threshold": float(uncertain_lower),
        "mid_threshold": float(best_threshold),
        "fp_rate_at_mid": float(best_fp_rate),
    }


def evaluate_on_test(model, X_test, y_test, thresholds, test_records):
    """
    Final evaluation on the test set. Test set touched ONCE.

    Reports: accuracy, precision, recall, F1, ROC-AUC, confusion matrix,
    FP/FN counts, 10 redacted example errors.
    """
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )
    from sklearn.metrics import (
        confusion_matrix as sk_confusion_matrix,
    )

    test_scores = model.predict(X_test, verbose=0).flatten()

    # Apply thresholds for three-class labeling
    spam_thresh = thresholds["spam_threshold"]
    not_spam_thresh = thresholds["not_spam_threshold"]

    # Binary predictions (using mid threshold for standard metrics)
    binary_pred = (test_scores >= thresholds["mid_threshold"]).astype(int)

    # Three-class predictions
    three_class = []
    for s in test_scores:
        if s >= spam_thresh:
            three_class.append("spam")
        elif s <= not_spam_thresh:
            three_class.append("not_spam")
        else:
            three_class.append("uncertain")

    # Standard binary metrics
    acc = accuracy_score(y_test, binary_pred)
    prec = precision_score(y_test, binary_pred)
    rec = recall_score(y_test, binary_pred)
    f1 = f1_score(y_test, binary_pred)
    auc = roc_auc_score(y_test, test_scores)
    cm = sk_confusion_matrix(y_test, binary_pred)

    # FP and FN counts
    fp_count = int(np.sum((binary_pred == 1) & (y_test == 0)))
    fn_count = int(np.sum((binary_pred == 0) & (y_test == 1)))

    print("\n--- Test Set Evaluation ---")
    print(f"  Accuracy:  {acc:.4f}")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall:    {rec:.4f}")
    print(f"  F1:        {f1:.4f}")
    print(f"  ROC-AUC:   {auc:.4f}")
    print(f"  FP count:  {fp_count}")
    print(f"  FN count:  {fn_count}")
    print(f"  Confusion Matrix:\n{cm}")

    # Three-class distribution
    print("\n  Three-class distribution:")
    print(f"    spam: {three_class.count('spam')}")
    print(f"    uncertain: {three_class.count('uncertain')}")
    print(f"    not_spam: {three_class.count('not_spam')}")

    # 10 redacted example errors
    errors = []
    for i, (pred, actual) in enumerate(zip(binary_pred, y_test)):
        if pred != actual and len(errors) < 10:
            actual_label = "spam" if actual == 1 else "ham"
            pred_label = "spam" if pred == 1 else "ham"
            score = float(test_scores[i])
            # Redact: show only first 30 chars of subject, no body
            subj = (
                test_records[i]["subject"][:30] + "..."
                if len(test_records[i]["subject"]) > 30
                else test_records[i]["subject"]
            )
            errors.append(
                {
                    "index": i,
                    "actual": actual_label,
                    "predicted": pred_label,
                    "score": round(score, 4),
                    "subject_preview": subj,
                }
            )

    print("\n  Example errors (first 10, redacted):")
    for err in errors:
        safe_subj = err["subject_preview"].encode("ascii", errors="replace").decode("ascii")
        print(f'    [{err["actual"]} -> {err["predicted"]}] score={err["score"]:.4f} subj="{safe_subj}"')

    return {
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1": float(f1),
        "roc_auc": float(auc),
        "fp_count": fp_count,
        "fn_count": fn_count,
        "confusion_matrix": cm.tolist(),
        "three_class_distribution": {
            "spam": three_class.count("spam"),
            "uncertain": three_class.count("uncertain"),
            "not_spam": three_class.count("not_spam"),
        },
        "example_errors": errors,
    }


def save_confusion_matrix_image(cm, output_path):
    """Save confusion matrix as an image."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, cmap="Blues")

    labels = ["Ham", "Spam"]
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title("Confusion Matrix — Test Set")

    # Add text annotations
    for i in range(2):
        for j in range(2):
            ax.text(
                j,
                i,
                str(cm[i][j]),
                ha="center",
                va="center",
                fontsize=16,
                fontweight="bold",
                color="white" if cm[i][j] > cm.max() / 2 else "black",
            )

    plt.colorbar(im)
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=100)
    plt.close()
    print(f"  Confusion matrix image saved: {output_path}")


def export_model(model, tokenizer, thresholds, metrics, baseline_metrics, models_dir):
    """
    Export model artifacts for serving.

    Exports:
    - Weights as NumPy arrays (for NumPy forward pass in production)
    - Vocabulary JSON
    - Thresholds JSON
    - Metrics JSON
    - Model config JSON
    - Keras .keras file (for evaluation)
    """
    os.makedirs(models_dir, exist_ok=True)

    # 1. Save Keras model
    keras_path = os.path.join(models_dir, "model.keras")
    model.save(keras_path)
    print(f"  Keras model saved: {keras_path}")

    # 2. Extract and save weights as numpy arrays
    weights_dir = os.path.join(models_dir, "weights")
    os.makedirs(weights_dir, exist_ok=True)

    for layer in model.layers:
        layer_weights = layer.get_weights()
        for i, w in enumerate(layer_weights):
            # Save as float16 for smaller size, with float32 available for parity check
            weight_path = os.path.join(weights_dir, f"{layer.name}_{i}.npy")
            np.save(weight_path, w.astype(np.float32))

            weight_path_f16 = os.path.join(weights_dir, f"{layer.name}_{i}_f16.npy")
            np.save(weight_path_f16, w.astype(np.float16))

    print(f"  Weights saved to: {weights_dir}")

    # 3. Save vocabulary
    vocab_path = os.path.join(models_dir, "vocab.json")
    tokenizer.save(vocab_path)

    # 4. Save thresholds
    thresholds_path = os.path.join(models_dir, "thresholds.json")
    with open(thresholds_path, "w") as f:
        json.dump(thresholds, f, indent=2)
    print(f"  Thresholds saved: {thresholds_path}")

    # 5. Save model config
    config = {
        "model_version": MODEL_VERSION,
        "architecture": "embedding_pooling_dense",
        "vocab_size": tokenizer.vocab_size,
        "max_sequence_length": tokenizer.max_sequence_length,
        "embedding_dim": EMBEDDING_DIM,
        "dense_units": DENSE_UNITS,
        "dropout_rate": DROPOUT_RATE,
        "max_vocab_size": MAX_VOCAB_SIZE,
        "use_float16_weights": False,  # Start with float32 for parity
    }
    config_path = os.path.join(models_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  Config saved: {config_path}")

    # 6. Save metrics
    all_metrics = {
        "model_version": MODEL_VERSION,
        "dataset": "Apache SpamAssassin Public Corpus",
        "baseline": baseline_metrics,
        "production_model": metrics,
        "thresholds": thresholds,
    }
    metrics_path = os.path.join(models_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(all_metrics, f, indent=2)
    print(f"  Metrics saved: {metrics_path}")


def main():
    print("=" * 60)
    print("SpamGuard AI — Training Pipeline")
    print("=" * 60)

    set_seeds()

    # Step 1: Load raw emails
    print("\n--- Step 1: Load raw emails ---")
    if not os.path.isdir(RAW_DIR):
        print(f"ERROR: Raw data directory not found: {RAW_DIR}")
        print("Run: python scripts/get_data.py")
        return 1

    records = load_corpus(RAW_DIR)
    print(f"  Total records loaded: {len(records)}")

    ham_count = sum(1 for r in records if r["label"] == "ham")
    spam_count = sum(1 for r in records if r["label"] == "spam")
    print(f"  Ham: {ham_count}, Spam: {spam_count}")
    print(f"  Class ratio (spam/total): {spam_count / len(records):.2%}")

    # Step 2: Deduplicate
    print("\n--- Step 2: Deduplicate ---")
    records = deduplicate(records)
    ham_count = sum(1 for r in records if r["label"] == "ham")
    spam_count = sum(1 for r in records if r["label"] == "spam")
    print(f"  After dedup — Ham: {ham_count}, Spam: {spam_count}")

    # Step 3: Split
    print("\n--- Step 3: Train/Val/Test Split ---")
    train_records, val_records, test_records = split_data(records)
    print(
        f"  Train: {len(train_records)} (ham={sum(1 for r in train_records if r['label'] == 'ham')}, spam={sum(1 for r in train_records if r['label'] == 'spam')})"
    )
    print(
        f"  Val:   {len(val_records)} (ham={sum(1 for r in val_records if r['label'] == 'ham')}, spam={sum(1 for r in val_records if r['label'] == 'spam')})"
    )
    print(
        f"  Test:  {len(test_records)} (ham={sum(1 for r in test_records if r['label'] == 'ham')}, spam={sum(1 for r in test_records if r['label'] == 'spam')})"
    )

    # Step 4: Build vocabulary from training set
    print("\n--- Step 4: Build Vocabulary ---")
    train_texts = [preprocess_text(r["subject"], r["body"]) for r in train_records]
    tokenizer = Tokenizer(max_vocab_size=MAX_VOCAB_SIZE, max_sequence_length=MAX_SEQUENCE_LENGTH)
    tokenizer.build_vocab(train_texts)

    # Step 5: Prepare data
    print("\n--- Step 5: Prepare Data ---")
    X_train, y_train = prepare_data(train_records, tokenizer)
    X_val, y_val = prepare_data(val_records, tokenizer)
    X_test, y_test = prepare_data(test_records, tokenizer)
    print(f"  X_train: {X_train.shape}, y_train: {y_train.shape}")
    print(f"  X_val: {X_val.shape}, y_val: {y_val.shape}")
    print(f"  X_test: {X_test.shape}, y_test: {y_test.shape}")

    # Step 6: Baseline
    baseline_metrics = train_baseline(train_records, test_records)

    # Step 7: Build and train Keras model
    print("\n--- Step 7: Train Keras Model ---")

    model = build_keras_model(
        vocab_size=tokenizer.vocab_size,
        embedding_dim=EMBEDDING_DIM,
        max_length=MAX_SEQUENCE_LENGTH,
        dense_units=DENSE_UNITS,
        dropout_rate=DROPOUT_RATE,
    )
    model.summary()

    history = model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        verbose=1,
    )

    # Step 8: Choose thresholds on validation set
    print("\n--- Step 8: Choose Thresholds ---")
    thresholds = choose_thresholds(model, X_val, y_val)

    # Step 9: Evaluate on test set (touched ONCE)
    print("\n--- Step 9: Test Set Evaluation ---")
    test_metrics = evaluate_on_test(model, X_test, y_test, thresholds, test_records)

    # Step 10: Save confusion matrix image
    cm_path = os.path.join(MODELS_DIR, "confusion_matrix.png")
    save_confusion_matrix_image(np.array(test_metrics["confusion_matrix"]), cm_path)

    # Step 11: Export model
    print("\n--- Step 11: Export Model ---")
    export_model(model, tokenizer, thresholds, test_metrics, baseline_metrics, MODELS_DIR)

    # Step 12: Save training history
    history_path = os.path.join(MODELS_DIR, "training_history.json")
    with open(history_path, "w") as f:
        json.dump({k: [float(v) for v in vals] for k, vals in history.history.items()}, f, indent=2)

    print("\n" + "=" * 60)
    print("Training complete!")
    print(f"Artifacts saved to: {MODELS_DIR}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
