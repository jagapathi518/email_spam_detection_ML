# Parity Gate Results

**Status:** ✅ PASSED

## Score Comparison

- Max absolute difference: 8.62e-08
- Mean absolute difference: 9.64e-09
- Tolerance: 1.00e-04
- Scores match: Yes

## Label Comparison

- Test set size: 889
- Label mismatches: 0
- Labels match: Yes

## Configuration

- Model: Keras Embedding + GlobalAveragePooling1D + Dense
- Serving: NumPy forward pass (float32 weights)
- Thresholds: spam >= 0.9, not_spam <= 0.6200000000000004
