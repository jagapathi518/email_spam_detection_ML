"""
SpamGuard AI — NumPy Forward Pass for Serving

This module implements the same forward pass as the Keras model
(Embedding + GlobalAveragePooling1D + Dense + ReLU + Dense + Sigmoid)
using only NumPy. No TensorFlow required at serving time.

Architecture (matches Keras model):
  Input: (batch, seq_len) int32 token IDs
  → Embedding lookup: (batch, seq_len, embed_dim)
  → Masked global average pooling: (batch, embed_dim)
  → Dense + ReLU: (batch, dense_units)
  → Dense + Sigmoid: (batch, 1)
"""

import json
import os
from typing import Optional

import numpy as np


class NumpyModel:
    """
    NumPy-only forward pass that replicates the Keras model behavior.

    Loads weights exported from the Keras model and runs inference
    without any TensorFlow dependency.
    """

    def __init__(self):
        self.embedding_weights: Optional[np.ndarray] = None
        self.dense1_kernel: Optional[np.ndarray] = None
        self.dense1_bias: Optional[np.ndarray] = None
        self.output_kernel: Optional[np.ndarray] = None
        self.output_bias: Optional[np.ndarray] = None
        self.config: Optional[dict] = None
        self.loaded = False

    def load(self, model_dir: str, use_float16: bool = False) -> None:
        """
        Load model weights from the exported NumPy files.

        Args:
            model_dir: Path to the model version directory (e.g., models/v1)
            use_float16: If True, load float16 weights (smaller, slightly less precise)
        """
        weights_dir = os.path.join(model_dir, "weights")
        suffix = "_f16" if use_float16 else ""

        # Load config
        config_path = os.path.join(model_dir, "config.json")
        with open(config_path) as f:
            self.config = json.load(f)

        # Load weights
        self.embedding_weights = np.load(os.path.join(weights_dir, f"embedding_0{suffix}.npy"))
        self.dense1_kernel = np.load(os.path.join(weights_dir, f"dense1_0{suffix}.npy"))
        self.dense1_bias = np.load(os.path.join(weights_dir, f"dense1_1{suffix}.npy"))
        self.output_kernel = np.load(os.path.join(weights_dir, f"output_0{suffix}.npy"))
        self.output_bias = np.load(os.path.join(weights_dir, f"output_1{suffix}.npy"))

        # Ensure float32 for computation (even if loaded as float16)
        if use_float16:
            self.embedding_weights = self.embedding_weights.astype(np.float32)
            self.dense1_kernel = self.dense1_kernel.astype(np.float32)
            self.dense1_bias = self.dense1_bias.astype(np.float32)
            self.output_kernel = self.output_kernel.astype(np.float32)
            self.output_bias = self.output_bias.astype(np.float32)

        self.loaded = True

    def predict(self, x: np.ndarray) -> np.ndarray:
        """
        Run forward pass on padded integer sequences.

        Args:
            x: numpy array of shape (batch_size, seq_len) with int32 token IDs

        Returns:
            numpy array of shape (batch_size,) with float32 scores in [0, 1]
        """
        if not self.loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        # Ensure 2D input
        if x.ndim == 1:
            x = x.reshape(1, -1)

        # Step 1: Embedding lookup
        # Shape: (batch, seq_len) -> (batch, seq_len, embed_dim)
        embedded = self.embedding_weights[x]

        # Step 2: Masked global average pooling
        # Create mask: 1 where token ID != 0 (PAD), 0 otherwise
        mask = (x != 0).astype(np.float32)  # (batch, seq_len)
        mask_expanded = mask[:, :, np.newaxis]  # (batch, seq_len, 1)

        # Apply mask and compute mean
        masked_embedded = embedded * mask_expanded  # Zero out padded positions
        token_counts = mask.sum(axis=1, keepdims=True)  # (batch, 1)
        token_counts = np.maximum(token_counts, 1.0)  # Avoid division by zero
        pooled = masked_embedded.sum(axis=1) / token_counts  # (batch, embed_dim)

        # Step 3: Dense1 + ReLU
        # No dropout at inference
        dense1_out = pooled @ self.dense1_kernel + self.dense1_bias
        dense1_out = np.maximum(dense1_out, 0.0)  # ReLU

        # Step 4: Output Dense + Sigmoid
        output = dense1_out @ self.output_kernel + self.output_bias
        output = 1.0 / (1.0 + np.exp(-np.clip(output, -500, 500)))  # Sigmoid

        return output.flatten()

    def predict_single(self, x: np.ndarray) -> float:
        """
        Run forward pass on a single padded integer sequence.

        Args:
            x: numpy array of shape (seq_len,) with int32 token IDs

        Returns:
            float score in [0, 1]
        """
        return float(self.predict(x.reshape(1, -1))[0])


def load_model(model_dir: str, use_float16: bool = False) -> NumpyModel:
    """
    Convenience function to load and return a NumpyModel.

    Args:
        model_dir: Path to model version directory
        use_float16: If True, load float16 weights

    Returns:
        Loaded NumpyModel ready for inference
    """
    model = NumpyModel()
    model.load(model_dir, use_float16=use_float16)
    return model
