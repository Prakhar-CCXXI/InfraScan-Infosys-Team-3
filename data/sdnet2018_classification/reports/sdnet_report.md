# SDNET2018 Classification - Consolidated Results

## Fold 0: Model Comparison (Identical Test Set Verified)

| model | roc_auc | pr_auc | pr_auc_ci95 | pr_auc_diff_vs_convnext_tiny | thr0.5_prec | thr0.5_rec | thr0.5_f1 | val_f1_prec | val_f1_rec | val_f1_f1 | val_recall90_prec | val_recall90_rec | val_recall90_f1 | val_recall90_fpr |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| convnext_tiny | 0.953 | 0.886 | [0.847, 0.917] | (reference) | 0.572 | 0.897 | 0.699 | 0.860 | 0.772 | 0.813 | 0.576 | 0.897 | 0.701 | 0.130 |
| densenet121 | 0.952 | 0.884 | [0.846, 0.918] | -0.001 [-0.015, +0.010] | 0.580 | 0.890 | 0.702 | 0.867 | 0.754 | 0.807 | 0.550 | 0.897 | 0.682 | 0.144 |
| efficientnet_b0 | 0.946 | 0.877 | [0.836, 0.912] | -0.009 [-0.022, +0.001] | 0.631 | 0.854 | 0.726 | 0.852 | 0.757 | 0.802 | 0.525 | 0.891 | 0.661 | 0.158 |
| mobilenet_v3_large | 0.942 | 0.867 | [0.827, 0.902] | -0.018 [-0.030, -0.009] | 0.653 | 0.840 | 0.735 | 0.847 | 0.731 | 0.785 | 0.542 | 0.878 | 0.670 | 0.146 |
