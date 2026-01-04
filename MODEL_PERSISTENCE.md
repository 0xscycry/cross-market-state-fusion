# Model Persistence & Training State

The RL agent's learning progress is automatically saved and can be resumed across sessions. This document explains how model persistence works.

---

## What Gets Saved

### 1. Neural Network Weights (`rl_model.safetensors`)

**Format**: SafeTensors (155 KB)

**Contains**:
- **Actor network** parameters (policy)
  - Input layer: 18 → 64
  - Hidden layers: 64 → 64 (with LayerNorm)
  - Output layer: 64 → 3 (softmax)
- **Critic network** parameters (value function)
  - Input layer: 18 → 96
  - Hidden layers: 96 → 96 (with LayerNorm)
  - Output layer: 96 → 1
- **TemporalEncoder** parameters (Phase 5+)
  - Processes last 5 states → 32-dim features

**Why SafeTensors**: Fast, secure, cross-platform format supported by MLX

### 2. Training Statistics (`rl_model_stats.npz`)

**Format**: NumPy compressed (2.6 KB)

**Contains**:
- `reward_mean`: Running mean for reward normalization
- `reward_std`: Running standard deviation for reward normalization
- `reward_count`: Number of rewards observed
- `input_dim`: 18 (state space size)
- `hidden_size`: 64/96 (network architecture)
- `history_len`: 5 (temporal context window)
- `temporal_dim`: 32 (compressed temporal features)

**Why this matters**: Reward normalization is critical for PPO stability. Without preserving these stats, loading a model would break the reward scale.

---

## When Does Saving Happen?

### Automatic Save on Exit

From `run.py`:
```python
finally:
    print("

Shutting down...")
    self.running = False
    self.price_streamer.stop()
    self.orderbook_streamer.stop()
    self.futures_streamer.stop()
    self.close_all_positions()
    self.print_final_stats()

    # Save RL model if training
    if isinstance(self.strategy, RLStrategy) and self.strategy.training:
        self.strategy.save("rl_model")
        print("  [RL] Model saved to rl_model.safetensors")
```

**Triggers**:
- ✅ Ctrl+C (KeyboardInterrupt)
- ✅ Exception/error during trading
- ✅ Natural shutdown (all markets expired)

**Important**: The model is **only saved in training mode** (`--train` flag). Inference mode doesn't modify the model, so no save is needed.

---

## Loading a Saved Model

### Resume Training

Continue training from where you left off:

```bash
python run.py --strategy rl --train --load rl_model --size 500
```

This:
1. Loads neural network weights from `rl_model.safetensors`
2. Loads reward normalization stats from `rl_model_stats.npz`
3. Continues training with PPO updates
4. Preserves learned patterns while adapting to new market conditions

### Inference Only

Use the trained model without further learning:

```bash
python run.py --strategy rl --load rl_model --size 500
```

(No `--train` flag)

This:
1. Loads the model weights
2. Sets model to eval mode (no gradient computation)
3. Trades using the learned policy
4. Does NOT update the model or save on exit

---

## Multiple Model Versions

You can save different model versions:

```bash
# Save to custom path
python run.py --strategy rl --train --load phase4_model --size 500
# On exit, saves to phase4_model.safetensors

# Load specific version
python run.py --strategy rl --train --load phase4_model
```

**Existing models in repo**:
- `rl_model.safetensors` - Latest Phase 5 model (temporal architecture)
- `rl_model_prob_pnl.safetensors` - Phase 3 model (probability-based PnL)

---

## What Happens During Save/Load

### Save Process

```python
def save(self, path: str):
    # 1. Flatten nested parameter dictionaries
    actor_flat = flatten_params(self.actor.parameters(), "actor.")
    critic_flat = flatten_params(self.critic.parameters(), "critic.")
    
    # 2. Combine and save weights
    weights = {**actor_flat, **critic_flat}
    mx.save_safetensors(f"{path}.safetensors", weights)
    
    # 3. Save training stats separately
    np.savez(
        f"{path}_stats.npz",
        reward_mean=self.reward_mean,
        reward_std=self.reward_std,
        reward_count=self.reward_count,
        input_dim=self.input_dim,
        hidden_size=self.hidden_size,
        history_len=self.history_len,
        temporal_dim=self.temporal_dim
    )
```

### Load Process

```python
def load(self, path: str):
    # 1. Load weights from SafeTensors
    weights = mx.load(f"{path}.safetensors")
    
    # 2. Unflatten and restore network parameters
    actor_params = unflatten_params(weights, "actor.", self.actor.parameters())
    critic_params = unflatten_params(weights, "critic.", self.critic.parameters())
    
    self.actor.update(actor_params)
    self.critic.update(critic_params)
    
    # 3. Load training stats
    stats = np.load(f"{path}_stats.npz")
    self.reward_mean = float(stats["reward_mean"])
    self.reward_std = float(stats["reward_std"])
    self.reward_count = int(stats["reward_count"])
    
    # 4. Set to eval mode (inference)
    mx.eval(self.actor.parameters())
    mx.eval(self.critic.parameters())
```

---

## What Doesn't Get Saved

### Replay Buffer

**Not saved**: The experience replay buffer (256 transitions)

**Why**: 
- Short-lived data (only for current training batch)
- Markets expire every 15 minutes - old experiences are stale
- Buffer refills quickly from live trading

**Implication**: When you restart training, the first PPO update happens after collecting 256 new experiences (~5-10 minutes).

### Trade History

**Not saved**: Historical trades and PnL

**Why**: Training logs are saved separately in `logs/updates_*.csv` (see TRAINING_JOURNAL.md)

**Alternative**: The logger saves:
- Per-trade metrics: entry/exit prices, PnL, duration
- Per-update metrics: policy loss, value loss, entropy, cumulative PnL
- CSVs can be analyzed post-training

### Market State

**Not saved**: Active positions, open prices, market subscriptions

**Why**: Markets expire every 15 minutes. On restart, the bot discovers fresh markets and starts clean.

---

## Training Continuity

### Reward Normalization

Critical for stable PPO training. From the code:

```python
# Update running statistics
self.reward_count += 1
self.reward_mean += (reward - self.reward_mean) / self.reward_count
self.reward_std = np.sqrt(
    (self.reward_std**2 * (self.reward_count - 1) + 
     (reward - self.reward_mean)**2) / self.reward_count
)

# Normalize rewards for training
norm_reward = (reward - self.reward_mean) / (self.reward_std + 1e-8)
```

When you load a model:
- ✅ Mean/std are restored → rewards stay normalized
- ✅ Policy gradients remain stable
- ✅ Training continues smoothly

Without saving stats:
- ❌ Rewards would have different scale
- ❌ Policy updates would be unstable
- ❌ Training would effectively restart

### Policy Updates

The model continues learning from where it left off:

1. **Exploration**: Entropy coefficient stays at 0.03 (low, refined policy)
2. **Value function**: Critic already knows approximate values
3. **Policy**: Actor already has learned patterns

New updates refine the policy based on fresh market data while preserving core patterns.

---

## Best Practices

### During Training

1. **Use consistent model name**: Stick to `rl_model` unless versioning
2. **Let it save on exit**: Don't kill -9, use Ctrl+C for clean shutdown
3. **Backup periodically**: Copy `.safetensors` and `_stats.npz` files

```bash
# Backup current model
cp rl_model.safetensors rl_model_backup_$(date +%Y%m%d).safetensors
cp rl_model_stats.npz rl_model_backup_$(date +%Y%m%d)_stats.npz
```

### Before Major Changes

4. **Save before architecture changes**: If modifying network structure, old weights won't load
5. **Version your models**: Use different names for different experiments

```bash
# Train with temporal architecture (Phase 5)
python run.py --strategy rl --train --load rl_model_phase5 --size 500

# Train with simpler architecture (Phase 4)
python run.py --strategy rl --train --load rl_model_phase4 --size 500
```

### Testing & Deployment

6. **Inference mode for evaluation**: Don't train on test data

```bash
# Paper trade with frozen policy
python run.py --strategy rl --load rl_model --size 100
```

7. **Keep training logs**: Match model checkpoints to CSV logs

```bash
ls -lh logs/updates_20251229_*.csv  # Find corresponding training session
```

---

## Troubleshooting

### "File not found: rl_model.safetensors"

**Cause**: No saved model exists yet

**Solution**: Train first without `--load`:
```bash
python run.py --strategy rl --train --size 50
# Let it run for 30+ minutes, then Ctrl+C
# Model will be saved automatically
```

### "Shape mismatch when loading weights"

**Cause**: Model architecture changed between save and load

**Solution**: 
- Delete old model files if architecture changed
- Use a new model name for the new architecture
- Check `input_dim`, `hidden_size`, `history_len` in code vs saved stats

### "Reward scale seems wrong after loading"

**Cause**: Stats file corrupted or not loaded

**Solution**:
- Check `rl_model_stats.npz` exists and matches `.safetensors` timestamp
- If missing, retrain from scratch (stats are critical)

### "Model not saving on exit"

**Cause**: Not in training mode or crash before save

**Solution**:
- Ensure `--train` flag is set
- Use Ctrl+C, not kill -9
- Check disk space (should be >10MB free)

---

## Model File Sizes

| File | Size | Contents |
|------|------|----------|
| `rl_model.safetensors` | ~155 KB | Neural network weights (actor + critic + temporal) |
| `rl_model_stats.npz` | ~2.6 KB | Reward normalization stats + architecture params |
| **Total** | **~158 KB** | Complete trained model |

For comparison:
- GPT-2 (small): 500 MB
- ResNet-50: 98 MB
- **This PPO agent**: 0.16 MB

Tiny models are viable because:
- Small state space (18 features)
- Simple task (hold/buy/sell)
- No image processing
- Focused domain (15-min binary markets)

---

## Cross-Session Training Example

### Session 1: Initial Training

```bash
$ python run.py --strategy rl --train --size 50
# Train for 2 hours
# Ctrl+C
# Output:
#   [RL] Model saved to rl_model.safetensors
#   Total PnL: +$123.45
#   Trades: 89
#   Win Rate: 21%
```

**Files created**:
- `rl_model.safetensors` (155 KB)
- `rl_model_stats.npz` (2.6 KB)
- `logs/updates_20251229_200254.csv` (trade history)

### Session 2: Resume Training

```bash
$ python run.py --strategy rl --train --load rl_model --size 100
# Continues from previous policy
# New trades use updated knowledge
# Train for 3 more hours
# Ctrl+C
# Output:
#   [RL] Model saved to rl_model.safetensors
#   Total PnL: +$456.78 (this session)
#   Trades: 134 (this session)
#   Win Rate: 23%
```

**Files updated**:
- `rl_model.safetensors` (overwritten with improved weights)
- `rl_model_stats.npz` (updated reward stats)
- `logs/updates_20251229_210225.csv` (new session log)

### Session 3: Inference (No Training)

```bash
$ python run.py --strategy rl --load rl_model --size 250
# Uses learned policy
# No PPO updates
# No save on exit
# Ctrl+C
# Output:
#   Total PnL: +$89.12
#   Trades: 45
#   Win Rate: 24%
```

**No files modified** (inference mode)

---

## Technical Details

### SafeTensors Format

Advantages over pickle/torch.save:
- **Fast**: Memory-mapped loading (no deserialization)
- **Safe**: No arbitrary code execution
- **Cross-platform**: Works on Apple Silicon, CUDA, CPU
- **Inspectable**: Can read metadata without loading full file

### MLX Framework

```python
import mlx.core as mx

# Save
mx.save_safetensors("model.safetensors", weights_dict)

# Load
weights = mx.load("model.safetensors")

# Eval mode (inference)
mx.eval(model.parameters())
```

**Why MLX**: Optimized for Apple Silicon (M1/M2/M3), unified memory, JIT compilation

---

## See Also

- [README.md](README.md) - Project overview and architecture
- [TRAINING_JOURNAL.md](TRAINING_JOURNAL.md) - Training evolution across 5 phases
- [strategies/rl_mlx.py](strategies/rl_mlx.py) - PPO implementation with save/load code
- [run.py](run.py) - Main training loop with automatic saving

---

*Last updated: January 4, 2025*
