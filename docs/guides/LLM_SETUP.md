# LLM Agent Setup Guide

This guide explains how to enable and use the LLM-powered agent for intelligent, dynamic tutoring.

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This installs:

- `langchain` - LLM framework
- `langchain-openai` - OpenAI integration
- `langchain-core` - Core components

### 2. Configure Your API Key

#### Option A: Create .env file (Recommended)

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API key
# Change this line:
OPENAI_API_KEY=sk-your-api-key-here
# To your actual key:
OPENAI_API_KEY=sk-proj-abc123...
```

#### Option B: Set environment variable

```bash
export OPENAI_API_KEY="sk-proj-abc123..."
export AGENT_TYPE="llm"
```

### 3. Run the Quiz

```bash
python3 test_terminal.py
```

You'll see:

```text
✓ Using LLM-powered agent
```

If you see this instead:

```text
✓ Using simple rule-based agent
```

Then the API key is not configured correctly.

## Configuration Options

### Agent Types

Edit `.env`:

```bash
# Use LLM agent (requires API key)
AGENT_TYPE=llm

# Use simple rule-based agent (no API key needed)
AGENT_TYPE=simple
```

### LLM Providers

#### OpenAI (Default)

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...
MODEL_NAME=gpt-4-turbo-preview
```

**Available Models:**

- `gpt-4-turbo-preview` - Most capable (recommended)
- `gpt-4` - Very capable
- `gpt-3.5-turbo` - Faster, cheaper

#### Anthropic Claude

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
MODEL_NAME=claude-3-opus-20240229
```

**Available Models:**

- `claude-3-opus-20240229` - Most capable
- `claude-3-sonnet-20240229` - Balanced
- `claude-3-haiku-20240307` - Fastest

### LLM Parameters

```bash
# Creativity (0.0-1.0, default: 0.7)
# Lower = more focused, Higher = more creative
AGENT_TEMPERATURE=0.7

# Max response length (default: 500)
AGENT_MAX_TOKENS=500
```

## How It Works

### System Architecture

```text
┌─────────────────────────────────────┐
│  Terminal Client                    │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  AgentFactory                       │  ← Chooses agent type
│  • Checks config                    │
│  • Validates API key                │
│  • Creates agent                    │
│  • Falls back if needed             │
└──────────────┬──────────────────────┘
               │
     ┌─────────┴─────────┐
     │                   │
┌────▼────────┐   ┌──────▼───────────┐
│ SimpleAgent │   │   LLMAgent       │
│ (fallback)  │   │   • LangChain    │
│             │   │   • GPT-4        │
│ Rule-based  │   │   • Curriculum   │
│ Templates   │   │     Context      │
└─────────────┘   └──────────────────┘
```

### LLM Agent Features

#### 1. Dynamic Responses

- Not template-based
- Adapts to student's specific errors
- Natural conversation flow

#### 2. Curriculum-Aware

- Loads vocabulary and problems
- References curriculum in system prompt
- Uses curriculum hints as guidance

#### 3. Socratic Method

- Asks guiding questions
- Never gives answers directly
- Builds on student explanations

#### 4. Error Handling

- Falls back to simple agent if LLM fails
- Continues working even without internet
- Graceful degradation

### Sample Interaction

#### With Simple Agent (Rule-Based)

```text
🤖 Agent: Hi Alice! Today we'll be studying multiplication! 
I'll give you 5 problems. Let's see how you do!

What is 7 × 8? 54

🤖 Agent: Hmm, I got a different answer. Let's think about this together.
🤖 Agent: Can you tell me how you calculated 7 × 8 = 54?
> I multiplied them

🤖 Agent: I see! Let me give you a hint: Try 7 × 10 and subtract 7 × 2

Let's try again. What is 7 × 8? 56
✓ Great work figuring that out!
```

#### With LLM Agent (GPT-4)

```text
🤖 Agent: Hi Alice! 🌟 I'm so excited to practice multiplication 
with you today! We'll work through 5 problems together. You've got this!

What is 7 × 8? 54

🤖 Agent: Hmm, that's close but not quite right. Let's figure this out together!

🤖 Agent: Can you walk me through your thinking? How did you get 54 for 7 × 8?
> I thought it was 7 times 8

🤖 Agent: I see you multiplied them! That's the right idea. Here's a hint: 
think about 7 groups of 8 items, or try breaking it down as (7 × 10) - (7 × 2). 
What do you get?

Let's try again. What is 7 × 8? 56
✓ Excellent work! You figured it out! 🎉
```

Notice how the LLM:

- Uses more natural language
- Is more encouraging and warm
- Provides more context in hints
- Adapts responses to the situation

## Testing

### Test Without API Key (Simple Agent)

```bash
# Don't set OPENAI_API_KEY
python3 test_terminal.py
```

Expected output:

```text
✓ Using simple rule-based agent
```

### Test With API Key (LLM Agent)

```bash
# Set API key in .env
echo "OPENAI_API_KEY=sk-proj-..." >> .env
echo "AGENT_TYPE=llm" >> .env

python3 test_terminal.py
```

Expected output:

```text
✓ Using LLM-powered agent
```

### Force Agent Type

You can override the config programmatically:

```python
from src.agents.agent_factory import AgentFactory

# Force simple agent
agent = AgentFactory.create_activity_agent("Alice", "math_mult_001", force_type="simple")

# Force LLM agent (will fail if not configured)
agent = AgentFactory.create_activity_agent("Alice", "math_mult_001", force_type="llm")
```

## Cost Considerations

### OpenAI Pricing (as of 2024)

**GPT-4 Turbo:**

- Input: $0.01 per 1K tokens
- Output: $0.03 per 1K tokens

**Typical Session Cost:**

- 5 problems with errors: ~10-15K tokens total
- Cost: ~$0.30-0.50 per session

**GPT-3.5 Turbo (Cheaper Alternative):**

- Input: $0.0005 per 1K tokens
- Output: $0.0015 per 1K tokens
- Cost: ~$0.01-0.02 per session

### Cost Optimization

1. **Use GPT-3.5 for development:**

   ```bash
   MODEL_NAME=gpt-3.5-turbo
   ```

2. **Reduce max_tokens:**

   ```bash
   AGENT_MAX_TOKENS=300  # Shorter responses
   ```

3. **Cache responses** (future enhancement)

4. **Use simple agent for known patterns**

## Troubleshooting

### "No API key configured"

**Problem:** Agent falls back to simple mode

**Solution:**

1. Check `.env` file exists
2. Verify `OPENAI_API_KEY` is set
3. Ensure no spaces around the `=`
4. Check key starts with `sk-proj-` or `sk-`

### "Rate limit exceeded"

**Problem:** Too many requests to OpenAI

**Solution:**

1. Wait a few minutes
2. Upgrade OpenAI plan
3. Use GPT-3.5-turbo (higher limits)

### "LLM agent initialization failed"

**Problem:** Import error or API error

**Solution:**

1. Reinstall dependencies: `pip install -r requirements.txt`
2. Check API key is valid
3. Check internet connection
4. View detailed error in terminal

### Responses are too long/short

**Problem:** Agent responses don't match desired length

**Solution:**

Adjust `AGENT_MAX_TOKENS`:

```bash
AGENT_MAX_TOKENS=300  # Shorter
AGENT_MAX_TOKENS=700  # Longer
```

## Next Steps

1. **Try different models** - Compare GPT-4 vs GPT-3.5 vs Claude
2. **Adjust temperature** - Make responses more/less creative
3. **Add more prompts** - Enhance system context for better responses
4. **Test edge cases** - See how agent handles unusual student inputs
5. **Build REST API** - Expose LLM agent via FastAPI

## Advanced: Custom System Prompts

You can customize the agent's behavior by editing `backend/src/agents/llm_agent.py`:

```python
def _build_system_context(self) -> str:
    return f"""You are a friendly, patient math tutor...
    
    NEW INSTRUCTION: Always use emojis
    NEW INSTRUCTION: Reference real-world examples
    etc.
    """
```

This allows you to fine-tune the teaching style!

## Support

If you encounter issues:

1. Check the terminal output for detailed errors
2. Verify `.env` configuration
3. Test with simple agent first
4. Review OpenAI API status: <https://status.openai.com>
