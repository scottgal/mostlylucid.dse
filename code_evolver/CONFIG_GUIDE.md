# mostlylucid DiSE Configuration Guide

## ⚠️ IMPORTANT: Don't Burn Anthropic Credits Accidentally!

This guide shows **EXACTLY** which configs are free (local Ollama) and which cost money (Anthropic cloud).

---

## ✅ FREE Configs (100% Local Ollama - No API Costs)

**Use these for FREE local-only operation:**

| Config File | Description | Backend |
|-------------|-------------|---------|
| `config.yaml` | **DEFAULT** - Complete unified config, all local | Ollama only |
| `config.unified.yaml` | Same as config.yaml, all local models | Ollama only |
| `config.local.yaml` | Explicitly local-only configuration | Ollama only |
| `config.local.minimal.yaml` | Minimal local config | Ollama only |

**To use:**
```bash
# Default (free)
python chat_cli.py

# Or explicit local
python chat_cli.py --config config.local.yaml
```

**Cost: $0** (100% free, uses your local Ollama models)

---

## ⚠️ PAID Configs (Anthropic Cloud - COSTS MONEY!)

**These configs use Anthropic API and WILL burn credits:**

| Config File | Description | Cost Per Workflow |
|-------------|-------------|-------------------|
| `config.anthropic.simple.yaml` | Simple Anthropic config | ~$0.15-$0.75 |
| `config.anthropic.unified.yaml` | Full Anthropic config | ~$0.15-$0.75 |
| `config.CLOUD_ANTHROPIC_COSTS_MONEY.minimal.yaml` | Minimal Anthropic (renamed for clarity) | ~$0.15-$0.75 |
| `config.CLOUD_HYBRID_COSTS_MONEY.yaml` | Hybrid cloud/local (renamed for clarity) | ~$0.15-$0.75 |

**To use (requires API key):**
```bash
# Set API key
export ANTHROPIC_API_KEY='sk-ant-api03-...'

# Run with paid config
python chat_cli.py --config config.anthropic.simple.yaml
```

**Cost: ~$0.15-$0.75 per workflow** (can add up quickly!)

---

## 🎯 Quick Decision Guide

**I want:** → **Use this config:**

- **FREE, unlimited usage** → `config.local.yaml` or `config.yaml` (default)
- **Best quality, willing to pay** → `config.anthropic.simple.yaml` (with API key)
- **Testing/prototyping** → `config.local.yaml` (free)
- **Production with budget** → `config.anthropic.unified.yaml` (with API key)

---

## ⚠️ How to Avoid Burning Credits Accidentally

### Problem: Confusing Config Names (OLD ISSUE - NOW FIXED)

**Before (confusing):**
```yaml
# config.hybrid.yaml  ← Unclear if it costs money
ollama:  # ← Says "ollama" but...
  models:
    overseer:
      backend: "anthropic"  # ← Actually uses Anthropic! Costs money!
```

**After (clear):**
```yaml
# config.CLOUD_HYBRID_COSTS_MONEY.yaml  ← VERY CLEAR NOW
# ⚠️ WARNING: THIS CONFIG USES ANTHROPIC API - COSTS REAL MONEY! ⚠️
ollama:  # ← MISLEADING NAME (legacy structure)
  models:
    overseer:
      backend: "anthropic"  # ← NOT ollama! This is Anthropic cloud! ⚠️
```

---

## 🛡️ Safety Checklist

**Before running mostlylucid DiSE:**

1. ✅ **Check filename**: Does it contain "CLOUD" or "COSTS_MONEY"?
   - YES → Will burn API credits
   - NO → Probably free (local Ollama)

2. ✅ **Read the header**: Open the config file and check the top
   - Look for: "⚠️ WARNING: COSTS REAL MONEY!" box
   - If present → Will burn credits

3. ✅ **Check backend setting**: Look for `backend: "anthropic"`
   - `backend: "ollama"` → Free (local)
   - `backend: "anthropic"` → Costs money (cloud)

4. ✅ **Default is safe**: If you don't specify `--config`, it uses `config.yaml` (free)

---

## ✅ Safe Defaults

**The system is configured to be SAFE by default:**

1. Default config (`config.yaml`) uses Ollama (free)
2. Anthropic backend is `enabled: false` in free configs
3. All Anthropic configs now have BIG WARNING BOXES
4. Filenames clearly indicate when they cost money

**You have to EXPLICITLY choose a paid config to burn credits.**

---

## 📞 Quick Reference

| Config | Command | Cost | Quality |
|--------|---------|------|---------|
| Default | `python chat_cli.py` | FREE | Good |
| Local | `python chat_cli.py --config config.local.yaml` | FREE | Good |
| Anthropic | `python chat_cli.py --config config.anthropic.simple.yaml` | PAID | Best |

---

**Summary:** Use `config.local.yaml` or `config.yaml` for FREE local operation. Only use configs with "CLOUD" or "anthropic" in the name when you're ready to pay for Anthropic API!
