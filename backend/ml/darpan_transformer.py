"""
DarpanAI — Transformer Architecture Definition (12-Feature ICMR Edition)
=========================================================================
This file must live in the backend so that torch.load() can resolve
the DarpanTransformer class. It is an exact copy of the class from
train_l40s_sequence.py (the GPU training script).

Architecture:
  - Input:  [batch, 30, 12]  — 30-day sequence of 12 ICMR features
  - Static features (0:7)  : age, gender, bmi, whr, fam_diabetes, fam_cvd, fam_hypertension
  - Dynamic features (7:12): sleep_hours, steps, sugar_intake_g, stress_level, hrv_rmssd
  - Output: [batch, 3]      — Diabetes%, CVD%, Hypertension% (0–100)
"""

import torch
import torch.nn as nn


class InputNormalizer(nn.Module):
    """Bakes normalisation stats natively into the model state_dict."""
    def __init__(self, norm_mean, norm_std):
        super().__init__()
        self.register_buffer("mean", torch.tensor(norm_mean, dtype=torch.float32))
        self.register_buffer("std",  torch.tensor(norm_std,  dtype=torch.float32) + 1e-8)

    def forward(self, x):
        return (x - self.mean) / self.std


class DarpanTransformer(nn.Module):
    """
    Hybrid Transformer with FiLM conditioning for longitudinal health data.
    Trained on the ICMR 12-feature dataset on an L40S GPU.
    Inference runs on Apple MPS or CPU without modification.
    """
    def __init__(self, norm_mean, norm_std, static_dim=7, dynamic_dim=5,
                 d_model=256, n_heads=8, n_layers=4):
        super().__init__()
        self.normalizer   = InputNormalizer(norm_mean, norm_std)
        self.static_dim   = static_dim
        self.dynamic_dim  = dynamic_dim

        # Static encoding path
        self.static_encoder = nn.Sequential(
            nn.Linear(static_dim, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Linear(128, 128),
        )

        # FiLM Generator (scale & shift the dynamic sequence with static context)
        self.film_gen = nn.Linear(128, d_model * 2)

        # Dynamic encoding path
        self.dynamic_proj = nn.Linear(dynamic_dim, d_model)
        self.pos_encoder  = nn.Parameter(torch.randn(1, 30, d_model))

        # Core Transformer
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=512,
            dropout=0.1,
            batch_first=True,
            norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)

        # 3 output heads: Diabetes, CVD, Hypertension
        combined_dim = d_model + 128

        def _head():
            return nn.Sequential(
                nn.Linear(combined_dim, 256),
                nn.GELU(),
                nn.Dropout(0.2),
                nn.Linear(256, 64),
                nn.GELU(),
                nn.Linear(64, 1),
            )

        self.head_diabetes     = _head()
        self.head_cvd          = _head()
        self.head_hypertension = _head()

    def forward(self, x):
        """x: [B, 30, 12] raw (unnormalized) feature tensor."""
        x = self.normalizer(x)

        static_x  = x[:, 0, :self.static_dim]   # [B, 7]
        dynamic_x = x[:, :, self.static_dim:]   # [B, 30, 5]

        # FiLM conditioning from static context
        s_emb = self.static_encoder(static_x)   # [B, 128]
        film  = self.film_gen(s_emb)            # [B, d_model*2]
        gamma, beta = torch.chunk(film, 2, dim=-1)
        gamma = gamma.unsqueeze(1)              # [B, 1, d_model]
        beta  = beta.unsqueeze(1)

        # Dynamic sequence
        seq_emb = self.dynamic_proj(dynamic_x) + self.pos_encoder  # [B, 30, d_model]
        seq_emb = seq_emb * (1.0 + gamma) + beta

        # Self-attention
        t_out    = self.transformer(seq_emb)    # [B, 30, d_model]
        pooled   = t_out.mean(dim=1)            # [B, d_model]

        final = torch.cat([pooled, s_emb], dim=-1)  # [B, d_model + 128]

        diab = self.head_diabetes(final)
        cvd  = self.head_cvd(final)
        hyp  = self.head_hypertension(final)

        return torch.cat([diab, cvd, hyp], dim=1)  # [B, 3]
