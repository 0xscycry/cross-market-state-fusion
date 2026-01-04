#!/usr/bin/env python3
"""
NumPy-based PPO (Proximal Policy Optimization) strategy.

Fallback implementation using NumPy instead of MLX for compatibility.
Implements PPO with manual gradient computation.

Key optimizations for 15-min binary markets:
- Temporal processing: captures momentum by attending to last N states
- Asymmetric architecture: larger critic (96) for better value estimation
- Lower gamma (0.95): appropriate for short-horizon trading
- Smaller buffer (256): faster adaptation to regime changes
"""
import numpy as np
from collections import deque
from typing import List, Dict, Optional
from dataclasses import dataclass
from .base import Strategy, MarketState, Action


@dataclass
class Experience:
    """Single experience tuple with temporal context."""
    state: np.ndarray  # Current state features (18,)
    temporal_state: np.ndarray  # Stacked temporal features (history_len * 18,)
    action: int
    reward: float
    next_state: np.ndarray
    next_temporal_state: np.ndarray
    done: bool
    log_prob: float
    value: float


class LayerNorm:
    """Layer normalization."""
    def __init__(self, dim: int, eps: float = 1e-5):
        self.dim = dim
        self.eps = eps
        self.gamma = np.ones(dim, dtype=np.float32)
        self.beta = np.zeros(dim, dtype=np.float32)
        
    def forward(self, x: np.ndarray) -> np.ndarray:
        mean = np.mean(x, axis=-1, keepdims=True)
        var = np.var(x, axis=-1, keepdims=True)
        x_norm = (x - mean) / np.sqrt(var + self.eps)
        return self.gamma * x_norm + self.beta
    
    def parameters(self):
        return [self.gamma, self.beta]


class Linear:
    """Linear layer with He initialization."""
    def __init__(self, in_features: int, out_features: int):
        self.in_features = in_features
        self.out_features = out_features
        # He initialization
        self.weight = np.random.randn(in_features, out_features).astype(np.float32) * np.sqrt(2.0 / in_features)
        self.bias = np.zeros(out_features, dtype=np.float32)
        
    def forward(self, x: np.ndarray) -> np.ndarray:
        return x @ self.weight + self.bias
    
    def parameters(self):
        return [self.weight, self.bias]


class TemporalEncoder:
    """Encodes temporal sequence of states into momentum/trend features.
    
    Takes last N states and compresses them into a fixed-size representation
    that captures velocity, acceleration, and trend direction.
    
    Architecture: (history_len * 18) → 64 → LayerNorm → tanh → 32
    Output is concatenated with current state features.
    """
    def __init__(self, input_dim: int = 18, history_len: int = 5, output_dim: int = 32):
        self.history_len = history_len
        self.temporal_input = input_dim * history_len
        self.fc1 = Linear(self.temporal_input, 64)
        self.ln1 = LayerNorm(64)
        self.fc2 = Linear(64, output_dim)
        self.ln2 = LayerNorm(output_dim)
        
    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass. x is (batch, history_len * input_dim)."""
        h = np.tanh(self.ln1.forward(self.fc1.forward(x)))
        h = np.tanh(self.ln2.forward(self.fc2.forward(h)))
        return h
    
    def parameters(self):
        params = []
        params.extend(self.fc1.parameters())
        params.extend(self.ln1.parameters())
        params.extend(self.fc2.parameters())
        params.extend(self.ln2.parameters())
        return params


class Actor:
    """Policy network with temporal awareness.
    
    Architecture:
        Current state (18) + Temporal features (32) = 50
        → 64 → LayerNorm → tanh → 64 → LayerNorm → tanh → 3 (softmax)
    
    Temporal encoder captures momentum/trends from state history.
    Smaller network (64) to prevent overfitting on enhanced features.
    """
    def __init__(self, input_dim: int = 18, hidden_size: int = 64, output_dim: int = 3,
                 history_len: int = 5, temporal_dim: int = 32):
        self.temporal_encoder = TemporalEncoder(input_dim, history_len, temporal_dim)
        
        # Combined input: current state + temporal features
        combined_dim = input_dim + temporal_dim
        self.fc1 = Linear(combined_dim, hidden_size)
        self.ln1 = LayerNorm(hidden_size)
        self.fc2 = Linear(hidden_size, hidden_size)
        self.ln2 = LayerNorm(hidden_size)
        self.fc3 = Linear(hidden_size, output_dim)
        
    def forward(self, current_state: np.ndarray, temporal_state: np.ndarray) -> np.ndarray:
        """Forward pass. Returns action probabilities.
        
        Args:
            current_state: (batch, 18) current features
            temporal_state: (batch, history_len * 18) stacked history
        """
        # Encode temporal context
        temporal_features = self.temporal_encoder.forward(temporal_state)
        
        # Combine current + temporal
        combined = np.concatenate([current_state, temporal_features], axis=-1)
        
        h = np.tanh(self.ln1.forward(self.fc1.forward(combined)))
        h = np.tanh(self.ln2.forward(self.fc2.forward(h)))
        logits = self.fc3.forward(h)
        
        # Softmax
        exp_logits = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)
        return probs
    
    def parameters(self):
        params = []
        params.extend(self.temporal_encoder.parameters())
        params.extend(self.fc1.parameters())
        params.extend(self.ln1.parameters())
        params.extend(self.fc2.parameters())
        params.extend(self.ln2.parameters())
        params.extend(self.fc3.parameters())
        return params


class Critic:
    """Value network with temporal awareness - ASYMMETRIC (larger than actor).
    
    Architecture:
        Current state (18) + Temporal features (32) = 50
        → 96 → LayerNorm → tanh → 96 → LayerNorm → tanh → 1
    
    Larger network (96 vs 64) because:
    - Value estimation is harder than policy
    - Critic doesn't overfit as easily (regresses to scalar)
    - Better value estimates improve advantage computation
    """
    def __init__(self, input_dim: int = 18, hidden_size: int = 96,
                 history_len: int = 5, temporal_dim: int = 32):
        self.temporal_encoder = TemporalEncoder(input_dim, history_len, temporal_dim)
        
        # Combined input: current state + temporal features
        combined_dim = input_dim + temporal_dim
        self.fc1 = Linear(combined_dim, hidden_size)
        self.ln1 = LayerNorm(hidden_size)
        self.fc2 = Linear(hidden_size, hidden_size)
        self.ln2 = LayerNorm(hidden_size)
        self.fc3 = Linear(hidden_size, 1)
        
    def forward(self, current_state: np.ndarray, temporal_state: np.ndarray) -> np.ndarray:
        """Forward pass. Returns value estimate.
        
        Args:
            current_state: (batch, 18) current features
            temporal_state: (batch, history_len * 18) stacked history
        """
        # Encode temporal context
        temporal_features = self.temporal_encoder.forward(temporal_state)
        
        # Combine current + temporal
        combined = np.concatenate([current_state, temporal_features], axis=-1)
        
        h = np.tanh(self.ln1.forward(self.fc1.forward(combined)))
        h = np.tanh(self.ln2.forward(self.fc2.forward(h)))
        value = self.fc3.forward(h)
        return value
    
    def parameters(self):
        params = []
        params.extend(self.temporal_encoder.parameters())
        params.extend(self.fc1.parameters())
        params.extend(self.ln1.parameters())
        params.extend(self.fc2.parameters())
        params.extend(self.ln2.parameters())
        params.extend(self.fc3.parameters())
        return params


class AdamOptimizer:
    """Adam optimizer."""
    def __init__(self, params: List[np.ndarray], lr: float = 1e-3, 
                 beta1: float = 0.9, beta2: float = 0.999, eps: float = 1e-8):
        self.params = params
        self.lr = lr
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = eps
        self.t = 0
        
        # Initialize moments
        self.m = [np.zeros_like(p) for p in params]
        self.v = [np.zeros_like(p) for p in params]
    
    def step(self, grads: List[np.ndarray]):
        """Update parameters with gradients."""
        self.t += 1
        
        for i, (param, grad) in enumerate(zip(self.params, grads)):
            # Update biased first moment estimate
            self.m[i] = self.beta1 * self.m[i] + (1 - self.beta1) * grad
            # Update biased second raw moment estimate
            self.v[i] = self.beta2 * self.v[i] + (1 - self.beta2) * (grad ** 2)
            
            # Compute bias-corrected moments
            m_hat = self.m[i] / (1 - self.beta1 ** self.t)
            v_hat = self.v[i] / (1 - self.beta2 ** self.t)
            
            # Update parameters
            param -= self.lr * m_hat / (np.sqrt(v_hat) + self.eps)


class RLStrategy(Strategy):
    """PPO-based strategy with temporal-aware actor-critic architecture using NumPy.
    
    Key features:
    - Temporal processing: maintains history of last N states to capture momentum
    - Asymmetric architecture: larger critic (96) for better value estimation
    - Lower gamma (0.95): appropriate for 15-min trading horizon
    - Smaller buffer (256): faster adaptation to regime changes
    """
    
    def __init__(
        self,
        input_dim: int = 18,
        hidden_size: int = 64,  # Actor hidden size
        critic_hidden_size: int = 96,  # Larger critic for better value estimation
        history_len: int = 5,  # Number of past states for temporal processing
        temporal_dim: int = 32,  # Temporal encoder output size
        lr_actor: float = 1e-4,
        lr_critic: float = 3e-4,
        gamma: float = 0.95,  # Lower gamma for 15-min horizon (was 0.99)
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        entropy_coef: float = 0.03,  # Lower entropy to allow sparse policy (mostly HOLD)
        value_coef: float = 0.5,
        max_grad_norm: float = 0.5,
        buffer_size: int = 256,  # Smaller buffer for faster adaptation (was 512)
        batch_size: int = 64,
        n_epochs: int = 10,
        target_kl: float = 0.02,
    ):
        super().__init__("rl")
        self.input_dim = input_dim
        self.hidden_size = hidden_size
        self.critic_hidden_size = critic_hidden_size
        self.history_len = history_len
        self.temporal_dim = temporal_dim
        self.output_dim = 3  # BUY, HOLD, SELL (simplified)
        
        # Hyperparameters
        self.lr_actor = lr_actor
        self.lr_critic = lr_critic
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.entropy_coef = entropy_coef
        self.value_coef = value_coef
        self.max_grad_norm = max_grad_norm
        self.buffer_size = buffer_size
        self.batch_size = batch_size
        self.n_epochs = n_epochs
        self.target_kl = target_kl
        
        # Networks with temporal processing
        self.actor = Actor(input_dim, hidden_size, self.output_dim, history_len, temporal_dim)
        self.critic = Critic(input_dim, critic_hidden_size, history_len, temporal_dim)
        
        # Optimizers
        self.actor_optimizer = AdamOptimizer(self.actor.parameters(), lr=lr_actor)
        self.critic_optimizer = AdamOptimizer(self.critic.parameters(), lr=lr_critic)
        
        # Experience buffer
        self.experiences: List[Experience] = []
        
        # Temporal state history (per-market, keyed by asset)
        self._state_history: Dict[str, deque] = {}
        
        # Running stats for reward normalization
        self.reward_mean = 0.0
        self.reward_std = 1.0
        self.reward_count = 0
        
        # For storing last action's log prob and value
        self._last_log_prob = 0.0
        self._last_value = 0.0
        self._last_temporal_state: Optional[np.ndarray] = None
    
    def _get_temporal_state(self, asset: str, current_features: np.ndarray) -> np.ndarray:
        """Get stacked temporal state for an asset.
        
        Maintains a history of the last N states per asset.
        Returns flattened array of shape (history_len * input_dim,).
        """
        if asset not in self._state_history:
            self._state_history[asset] = deque(maxlen=self.history_len)
        
        history = self._state_history[asset]
        
        # Add current state to history
        history.append(current_features.copy())
        
        # Pad with zeros if not enough history
        if len(history) < self.history_len:
            padding = [np.zeros(self.input_dim, dtype=np.float32)] * (self.history_len - len(history))
            stacked = np.concatenate(padding + list(history))
        else:
            stacked = np.concatenate(list(history))
        
        return stacked.astype(np.float32)
    
    def act(self, state: MarketState) -> Action:
        """Select action using current policy with temporal context."""
        features = state.to_features()
        
        # Get temporal state (stacked history)
        temporal_state = self._get_temporal_state(state.asset, features)
        
        # Reshape for batch dimension
        features_batch = features.reshape(1, -1)
        temporal_batch = temporal_state.reshape(1, -1)
        
        # Get action probabilities and value with temporal context
        probs = self.actor.forward(features_batch, temporal_batch)
        value = self.critic.forward(features_batch, temporal_batch)
        
        probs_np = probs[0]
        value_np = float(value[0, 0])
        
        if self.training:
            # Sample from distribution
            action_idx = np.random.choice(self.output_dim, p=probs_np)
        else:
            # Greedy
            action_idx = int(np.argmax(probs_np))
        
        # Store for experience collection
        self._last_log_prob = float(np.log(probs_np[action_idx] + 1e-8))
        self._last_value = value_np
        self._last_temporal_state = temporal_state
        
        return Action(action_idx)
    
    def store(self, state: MarketState, action: Action, reward: float,
              next_state: MarketState, done: bool):
        """Store experience for training with temporal context."""
        # Update running reward stats for normalization
        self.reward_count += 1
        delta = reward - self.reward_mean
        self.reward_mean += delta / self.reward_count
        self.reward_std = np.sqrt(
            ((self.reward_count - 1) * self.reward_std**2 + delta * (reward - self.reward_mean))
            / max(1, self.reward_count)
        )
        
        # Normalize reward
        norm_reward = (reward - self.reward_mean) / (self.reward_std + 1e-8)
        
        # Get next temporal state (updates history with next_state)
        next_features = next_state.to_features()
        next_temporal_state = self._get_temporal_state(next_state.asset, next_features)
        
        exp = Experience(
            state=state.to_features(),
            temporal_state=self._last_temporal_state if self._last_temporal_state is not None else np.zeros(self.history_len * self.input_dim, dtype=np.float32),
            action=action.value,
            reward=norm_reward,
            next_state=next_features,
            next_temporal_state=next_temporal_state,
            done=done,
            log_prob=self._last_log_prob,
            value=self._last_value,
        )
        self.experiences.append(exp)
        
        # Limit buffer size
        if len(self.experiences) > self.buffer_size:
            self.experiences = self.experiences[-self.buffer_size:]
    
    def _compute_gae(self, rewards: np.ndarray, values: np.ndarray,
                     dones: np.ndarray, next_value: float) -> tuple:
        """Compute Generalized Advantage Estimation."""
        n = len(rewards)
        advantages = np.zeros(n)
        returns = np.zeros(n)
        
        gae = 0
        for t in reversed(range(n)):
            if t == n - 1:
                next_val = next_value
            else:
                next_val = values[t + 1]
            
            # TD error
            delta = rewards[t] + self.gamma * next_val * (1 - dones[t]) - values[t]
            
            # GAE
            gae = delta + self.gamma * self.gae_lambda * (1 - dones[t]) * gae
            advantages[t] = gae
            returns[t] = advantages[t] + values[t]
        
        return advantages, returns
    
    def _clip_gradients(self, grads: List[np.ndarray]) -> List[np.ndarray]:
        """Clip gradients by global norm."""
        total_norm = np.sqrt(sum(np.sum(g ** 2) for g in grads))
        clip_coef = self.max_grad_norm / (total_norm + 1e-6)
        
        if clip_coef < 1.0:
            grads = [g * clip_coef for g in grads]
        
        return grads
    
    def update(self) -> Optional[Dict[str, float]]:
        """Update policy using PPO with manual gradient computation and temporal context."""
        if len(self.experiences) < self.buffer_size:
            return None
        
        # Convert experiences to arrays (including temporal states)
        states = np.array([e.state for e in self.experiences], dtype=np.float32)
        temporal_states = np.array([e.temporal_state for e in self.experiences], dtype=np.float32)
        actions = np.array([e.action for e in self.experiences], dtype=np.int32)
        rewards = np.array([e.reward for e in self.experiences], dtype=np.float32)
        dones = np.array([e.done for e in self.experiences], dtype=np.float32)
        old_log_probs = np.array([e.log_prob for e in self.experiences], dtype=np.float32)
        old_values = np.array([e.value for e in self.experiences], dtype=np.float32)
        
        # Compute next value for GAE (with temporal context)
        next_state_batch = self.experiences[-1].next_state.reshape(1, -1)
        next_temporal_batch = self.experiences[-1].next_temporal_state.reshape(1, -1)
        next_value = float(self.critic.forward(next_state_batch, next_temporal_batch)[0, 0])
        
        # Compute advantages and returns
        advantages, returns = self._compute_gae(rewards, old_values, dones, next_value)
        
        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        n_samples = len(self.experiences)
        all_metrics = {
            "policy_loss": [],
            "value_loss": [],
            "entropy": [],
            "approx_kl": [],
            "clip_fraction": [],
        }
        
        # Multiple epochs over the data
        for epoch in range(self.n_epochs):
            # Shuffle indices
            indices = np.random.permutation(n_samples)
            
            epoch_kl = 0.0
            n_batches = 0
            
            for start in range(0, n_samples, self.batch_size):
                end = min(start + self.batch_size, n_samples)
                batch_idx = indices[start:end]
                
                # Get batch
                batch_states = states[batch_idx]
                batch_temporal = temporal_states[batch_idx]
                batch_actions = actions[batch_idx]
                batch_old_log_probs = old_log_probs[batch_idx]
                batch_advantages = advantages[batch_idx]
                batch_returns = returns[batch_idx]
                batch_old_values = old_values[batch_idx]
                
                # Forward pass for actor
                probs = self.actor.forward(batch_states, batch_temporal)
                
                # Get log probs for taken actions
                batch_size_local = len(batch_idx)
                selected_probs = probs[np.arange(batch_size_local), batch_actions]
                log_probs = np.log(selected_probs + 1e-8)
                
                # PPO clipped objective
                ratio = np.exp(log_probs - batch_old_log_probs)
                surr1 = ratio * batch_advantages
                surr2 = np.clip(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * batch_advantages
                policy_loss = -np.mean(np.minimum(surr1, surr2))
                
                # Entropy bonus
                entropy = -np.sum(probs * np.log(probs + 1e-8), axis=-1)
                entropy_mean = np.mean(entropy)
                policy_loss_total = policy_loss - self.entropy_coef * entropy_mean
                
                # Compute approximate KL and clip fraction
                approx_kl = np.mean(batch_old_log_probs - log_probs)
                clip_frac = np.mean((np.abs(ratio - 1.0) > self.clip_epsilon).astype(np.float32))
                
                # Backward pass for actor (simplified - just compute simple gradients)
                # In practice, you'd use autograd. Here we use a simple gradient estimate.
                actor_params = self.actor.parameters()
                actor_grads = [np.zeros_like(p) for p in actor_params]
                
                # Approximate gradients with finite differences (for demonstration)
                epsilon = 1e-4
                for i, param in enumerate(actor_params):
                    grad = np.zeros_like(param)
                    flat_param = param.flatten()
                    for j in range(min(len(flat_param), 100)):  # Sample subset for speed
                        original = flat_param[j]
                        
                        flat_param[j] = original + epsilon
                        param_plus = flat_param.reshape(param.shape)
                        actor_params[i] = param_plus
                        probs_plus = self.actor.forward(batch_states, batch_temporal)
                        selected_plus = probs_plus[np.arange(batch_size_local), batch_actions]
                        log_probs_plus = np.log(selected_plus + 1e-8)
                        ratio_plus = np.exp(log_probs_plus - batch_old_log_probs)
                        surr_plus = np.minimum(ratio_plus * batch_advantages, 
                                              np.clip(ratio_plus, 1-self.clip_epsilon, 1+self.clip_epsilon) * batch_advantages)
                        loss_plus = -np.mean(surr_plus)
                        
                        flat_param[j] = original
                        grad.flatten()[j] = (loss_plus - policy_loss) / epsilon
                    
                    actor_grads[i] = grad
                
                # Clip and apply actor gradients
                actor_grads = self._clip_gradients(actor_grads)
                self.actor_optimizer.step(actor_grads)
                
                # Forward pass for critic
                values = self.critic.forward(batch_states, batch_temporal).squeeze()
                
                # Value loss with clipping
                values_clipped = batch_old_values + np.clip(
                    values - batch_old_values, -self.clip_epsilon, self.clip_epsilon
                )
                value_loss1 = (batch_returns - values) ** 2
                value_loss2 = (batch_returns - values_clipped) ** 2
                value_loss = 0.5 * np.mean(np.maximum(value_loss1, value_loss2))
                
                # Backward pass for critic (simplified)
                critic_params = self.critic.parameters()
                critic_grads = [np.zeros_like(p) for p in critic_params]
                
                # Approximate gradients
                epsilon = 1e-4
                for i, param in enumerate(critic_params):
                    grad = np.zeros_like(param)
                    flat_param = param.flatten()
                    for j in range(min(len(flat_param), 100)):
                        original = flat_param[j]
                        
                        flat_param[j] = original + epsilon
                        param_plus = flat_param.reshape(param.shape)
                        critic_params[i] = param_plus
                        values_plus = self.critic.forward(batch_states, batch_temporal).squeeze()
                        values_clipped_plus = batch_old_values + np.clip(
                            values_plus - batch_old_values, -self.clip_epsilon, self.clip_epsilon
                        )
                        loss_plus = 0.5 * np.mean(np.maximum((batch_returns - values_plus)**2, 
                                                             (batch_returns - values_clipped_plus)**2))
                        
                        flat_param[j] = original
                        grad.flatten()[j] = (loss_plus - value_loss) / epsilon
                    
                    critic_grads[i] = grad
                
                # Clip and apply critic gradients
                critic_grads = self._clip_gradients(critic_grads)
                self.critic_optimizer.step(critic_grads)
                
                # Record metrics
                all_metrics["policy_loss"].append(float(policy_loss))
                all_metrics["value_loss"].append(float(value_loss))
                all_metrics["entropy"].append(float(entropy_mean))
                all_metrics["approx_kl"].append(float(approx_kl))
                all_metrics["clip_fraction"].append(float(clip_frac))
                
                epoch_kl += float(approx_kl)
                n_batches += 1
            
            # Early stopping on KL divergence
            avg_kl = epoch_kl / max(1, n_batches)
            if avg_kl > self.target_kl:
                print(f"  [RL] Early stop epoch {epoch}, KL={avg_kl:.4f}")
                break
        
        # Clear buffer after update
        self.experiences.clear()
        
        # Compute explained variance
        y_pred = old_values
        y_true = returns
        var_y = np.var(y_true)
        explained_var = 1 - np.var(y_true - y_pred) / (var_y + 1e-8) if var_y > 0 else 0.0
        
        return {
            "policy_loss": np.mean(all_metrics["policy_loss"]),
            "value_loss": np.mean(all_metrics["value_loss"]),
            "entropy": np.mean(all_metrics["entropy"]),
            "approx_kl": np.mean(all_metrics["approx_kl"]),
            "clip_fraction": np.mean(all_metrics["clip_fraction"]),
            "explained_variance": explained_var,
        }
    
    def reset(self):
        """Clear experience buffer and state history."""
        self.experiences.clear()
        self._state_history.clear()
        self._last_temporal_state = None
    
    def save(self, path: str):
        """Save model and training state."""
        # Save all parameters
        save_dict = {
            'actor_params': self.actor.parameters(),
            'critic_params': self.critic.parameters(),
            'reward_mean': self.reward_mean,
            'reward_std': self.reward_std,
            'reward_count': self.reward_count,
            'input_dim': self.input_dim,
            'hidden_size': self.hidden_size,
            'critic_hidden_size': self.critic_hidden_size,
            'history_len': self.history_len,
            'temporal_dim': self.temporal_dim,
            'gamma': self.gamma,
            'buffer_size': self.buffer_size,
        }
        np.savez(path, **save_dict)
    
    def load(self, path: str):
        """Load model and training state."""
        data = np.load(path, allow_pickle=True)
        
        # Load parameters
        actor_params = data['actor_params']
        critic_params = data['critic_params']
        
        for i, param in enumerate(self.actor.parameters()):
            param[:] = actor_params[i]
        
        for i, param in enumerate(self.critic.parameters()):
            param[:] = critic_params[i]
        
        # Load stats
        self.reward_mean = float(data['reward_mean'])
        self.reward_std = float(data['reward_std'])
        self.reward_count = int(data['reward_count'])
