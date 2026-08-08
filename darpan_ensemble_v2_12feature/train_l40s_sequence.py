"""
DarpanAI — L40S Transformer Sequence Trainer (12-Feature ICMR Edition)
======================================================================
Replaces the vanilla 2-layer LSTM with our Hybrid Transformer + FiLM architecture,
now adapted for the new 12-feature ICMR dataset.

Input  : timeseries_health_data_icmr.csv  (from generate_timeseries_data.py)
Output : darpan_sequence_model_icmr.pth

Architecture:
  - 12 Features total (7 static, 5 dynamic)
  - InputNormalizer baked directly into model state_dict
  - Static features (age, gender, whr, genetics) encoded separately
  - Dynamic features pass through Transformer with FiLM conditioning
  - 3 parallel FC heads (predicting 0-100 directly)
"""

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, random_split
import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm

# ─── Config ──────────────────────────────────────────────────────────────────
DAYS_PER_USER = 30
BATCH_SIZE    = 512
EPOCHS        = 30
LR            = 3e-4      # Transformer usually likes 3e-4 or 1e-4 with warmup

# 12 ICMR features 
FEATURE_COLS = [
    "age", "gender", "bmi", "whr",
    "fam_diabetes", "fam_cvd", "fam_hypertension",
    "sleep_hours", "steps", "sugar_intake_g",
    "stress_level", "hrv_rmssd"
]
STATIC_DIM  = 7   # First 7 columns are static
DYNAMIC_DIM = 5   # Last 5 are dynamic
NUM_FEATURES = len(FEATURE_COLS) 

TARGET_COLS = ["target_diabetes", "target_cvd", "target_hypertension"]
# ─────────────────────────────────────────────────────────────────────────────

class ICMRSequenceDataset(Dataset):
    def __init__(self, csv_path):
        print(f"Loading ICMR dataset from {csv_path}...")
        df = pd.read_csv(csv_path)

        # For the normalizer, calculate means and stds across the entire dataset
        self.feature_means = df[FEATURE_COLS].mean().values
        self.feature_stds  = df[FEATURE_COLS].std().values

        self.X = []
        self.y = []

        print("Building 3D tensors [users, days, features]...")
        grouped = df.groupby("user_id")
        for _, group in tqdm(grouped, desc="Assembling Sequences"):
            seq = group[FEATURE_COLS].values[:DAYS_PER_USER]
            # Keeping targets in 0-100 range directly!
            target = group[TARGET_COLS].iloc[0].values
            self.X.append(seq)
            self.y.append(target)

        self.X = torch.tensor(np.array(self.X), dtype=torch.float32)
        self.y = torch.tensor(np.array(self.y), dtype=torch.float32)
        print(f"Tensor shape: X={self.X.shape}  y={self.y.shape}")

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


class InputNormalizer(nn.Module):
    """Bakes the normalisation stats natively into the model weights."""
    def __init__(self, norm_mean, norm_std):
        super(InputNormalizer, self).__init__()
        self.register_buffer('mean', torch.tensor(norm_mean, dtype=torch.float32))
        self.register_buffer('std',  torch.tensor(norm_std,  dtype=torch.float32) + 1e-8)

    def forward(self, x):
        return (x - self.mean) / self.std


class DarpanTransformer(nn.Module):
    """
    Hybrid Transformer with FiLM conditioning for longitudinal health data.
    """
    def __init__(self, norm_mean, norm_std, static_dim=7, dynamic_dim=5, d_model=256, n_heads=8, n_layers=4):
        super(DarpanTransformer, self).__init__()
        self.normalizer = InputNormalizer(norm_mean, norm_std)
        self.static_dim = static_dim
        self.dynamic_dim = dynamic_dim

        # Static encoding path
        self.static_encoder = nn.Sequential(
            nn.Linear(static_dim, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Linear(128, 128)
        )

        # FiLM Generator (Shift & Scale) for Transformer inputs
        self.film_gen = nn.Linear(128, d_model * 2)

        # Dynamic encoding path
        self.dynamic_proj = nn.Linear(dynamic_dim, d_model)
        self.pos_encoder  = nn.Parameter(torch.randn(1, 30, d_model))

        # Core Sequence Model
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=512, 
            dropout=0.1, batch_first=True, norm_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)

        # Output Heads (Predicting 0-100 directly)
        combined_dim = d_model + 128
        def _head():
            return nn.Sequential(
                nn.Linear(combined_dim, 256),
                nn.GELU(),
                nn.Dropout(0.2),
                nn.Linear(256, 64),
                nn.GELU(),
                nn.Linear(64, 1)
            )

        self.head_diabetes     = _head()
        self.head_cvd          = _head()
        self.head_hypertension = _head()

    def forward(self, x):
        # x is [B, 30, 12] raw feature matrix
        x = self.normalizer(x)

        # Split features
        static_x  = x[:, 0, :self.static_dim]       # [B, 7]
        dynamic_x = x[:, :, self.static_dim:]       # [B, 30, 5]

        # Process static context
        s_emb = self.static_encoder(static_x)       # [B, 128]
        film_params = self.film_gen(s_emb)          # [B, d_model * 2]
        gamma, beta = torch.chunk(film_params, 2, dim=-1) # [B, d_model] each
        gamma = gamma.unsqueeze(1)                  # [B, 1, d_model]
        beta  = beta.unsqueeze(1)                   # [B, 1, d_model]

        # Prepare dynamic sequence
        seq_emb = self.dynamic_proj(dynamic_x) + self.pos_encoder # [B, 30, d_model]

        # Apply FiLM Conditioning
        seq_emb = seq_emb * (1.0 + gamma) + beta

        # Self-Attention
        t_out = self.transformer(seq_emb)           # [B, 30, d_model]

        # Global average pooling
        pooled_t_out = t_out.mean(dim=1)            # [B, d_model]

        # Combine static and dynamic for final prediction
        final_rep = torch.cat([pooled_t_out, s_emb], dim=-1) # [B, d_model + 128]

        diab = self.head_diabetes(final_rep)
        cvd  = self.head_cvd(final_rep)
        hyp  = self.head_hypertension(final_rep)

        return torch.cat([diab, cvd, hyp], dim=1)


def train():
    import gc
    torch.cuda.empty_cache()
    gc.collect()
    torch.backends.cudnn.benchmark = True  # GPU optimization

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n{'='*55}")
    print(f"  DarpanAI Transformer Trainer — 12-Feature ICMR")
    print(f"  Device   : {device.type.upper()}")
    print(f"{'='*55}\n")

    csv_path = Path(__file__).parent / "timeseries_health_data_icmr.csv"
    if not csv_path.exists():
        print("ERROR: Data missing.")
        return

    dataset = ICMRSequenceDataset(csv_path)

    train_size = int(0.85 * len(dataset))
    val_size   = len(dataset) - train_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size], generator=torch.Generator().manual_seed(42))

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=4, pin_memory=True, drop_last=False)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True)

    # Initialize model with normalisation constants
    model = DarpanTransformer(
        norm_mean=dataset.feature_means,
        norm_std=dataset.feature_stds
    ).to(device)

    # Use HuberLoss because values are 0-100 and it's robust to outliers
    criterion = nn.HuberLoss(delta=5.0)
    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    
    # Cosine Annealing with linear warmup manually implemented via lambda
    warmup_epochs = 2
    def lr_lambda(epoch):
        if epoch < warmup_epochs:
            return float(epoch + 1) / float(warmup_epochs)
        decay_period = EPOCHS - warmup_epochs
        # Equivalent to CosineAnnealing
        pct = (epoch - warmup_epochs) / decay_period
        return 0.5 * (1.0 + np.cos(np.pi * pct))

    scheduler = optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    save_path = Path(__file__).parent / "darpan_sequence_model_icmr.pth"
    best_r2 = -float("inf")

    from sklearn.metrics import r2_score, mean_absolute_error

    scaler = torch.cuda.amp.GradScaler() # Mixed precision

    for epoch in range(1, EPOCHS + 1):
        # ── Train ─────────────────────────────────────────────────────────────
        model.train()
        train_loss = 0.0
        for x_batch, y_batch in train_loader:
            x_batch = x_batch.to(device, non_blocking=True)
            y_batch = y_batch.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)

            with torch.cuda.amp.autocast():
                preds = model(x_batch)
                loss  = criterion(preds, y_batch)

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()

            train_loss += loss.item()

        # ── Validate ──────────────────────────────────────────────────────────
        model.eval()
        val_preds_all, val_y_all = [], []
        with torch.no_grad(), torch.cuda.amp.autocast():
            for x_batch, y_batch in val_loader:
                x_batch = x_batch.to(device, non_blocking=True)
                preds = model(x_batch)
                val_preds_all.append(preds.cpu())
                val_y_all.append(y_batch)

        val_preds_all = torch.cat(val_preds_all).numpy()
        val_y_all = torch.cat(val_y_all).numpy()

        r2 = r2_score(val_y_all, val_preds_all)
        mae = mean_absolute_error(val_y_all, val_preds_all)
        
        current_lr = optimizer.param_groups[0]['lr']
        try:
            mem = torch.cuda.max_memory_allocated() / 1024**3
        except:
            mem = 0.0

        marker = ""
        if r2 > best_r2:
            best_r2, marker = r2, " ◀ best"
            torch.save(model.state_dict(), save_path)

        scheduler.step()

        print(f"Epoch {epoch:02d}/{EPOCHS} "
              f" Loss={train_loss/len(train_loader):.4f} "
              f" Val_R²={r2:.4f}  Val_MAE={mae:.2f}% "
              f" LR={current_lr:.2e}  [VRAM={mem:.2f}GB] {marker}")

    print(f"\n=======================================================")
    print(f"  Training Complete! Best Val R²: {best_r2:.4f}")
    print(f"  Model ready at: {save_path.name}")
    print(f"=======================================================\n")

if __name__ == "__main__":
    train()
