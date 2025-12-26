# Claude.ai Conversations Export

Export your full Claude conversation history (with complete message context) to markdown format for importing into NotebookLM or archiving.

## Features

- ✅ Full conversation context extraction (not just titles)
- ✅ Browser-based scraping of claude.ai via Playwright
- ✅ Markdown export format (NotebookLM compatible)
- ✅ JSON export for data analysis
- ✅ Progress tracking and resumable state
- ✅ Rate limiting to avoid server strain
- ✅ Automatic state saving (can resume if interrupted)

## Setup

### 1. Clone & Install

```bash
git clone https://github.com/mapachekurt/claude-conversations-export.git
cd claude-conversations-export
pip install -r requirements.txt
```

### 2. Run Export

#### Option A: Interactive (with browser window visible)

```bash
python export_claude_conversations.py --headless false
```

The browser will open. You'll be prompted to log in if needed. Then press Enter to continue extraction.

#### Option B: Headless (runs in background)

```bash
python export_claude_conversations.py --headless true --output ./exports
```

#### Option C: Specific formats

```bash
# Markdown only
python export_claude_conversations.py --formats markdown

# Both markdown and JSON
python export_claude_conversations.py --formats markdown,json
```

## Using in Claude Code (Web)

This is designed as a **long-running async job** perfect for Claude Code Web:

1. Clone the repo or create it fresh in Claude Code
2. Claude Code will prompt to install dependencies
3. Run the script from the terminal
4. It will extract all conversations and save to `./exports/`
5. Download the resulting `.md` file from Claude Code's file browser
6. Upload to NotebookLM

### Expected Runtime

- **100 conversations**: ~5-10 minutes
- **500 conversations**: ~20-30 minutes
- **1000+ conversations**: 1-2+ hours (depending on message volume)

The script tracks progress and can be resumed if interrupted.

## Output Files

After running, you'll find:

```
./exports/
├── claude_conversations.md      # NotebookLM import file
├── claude_conversations.json    # Raw data (for analysis)
├── export_state.json            # Progress checkpoint
└── export.log                   # Detailed execution log
```

## Resuming Interrupted Exports

If the script is interrupted, just run it again. It will:
1. Load the previous state from `export_state.json`
2. Continue from where it left off
3. Merge with any new conversations found

## Troubleshooting

### "Playwright not installed"
```bash
pip install playwright
playwright install
```

### Browser hangs during extraction
- This is normal for large exports
- The script includes timeouts and will continue
- Check `export.log` for detailed progress

### Only getting partial conversations
- Ensure you're logged into claude.ai
- The script waits for page loads but some conversations may have loading delays
- Increase timeout in code if needed

## Import to NotebookLM

1. Go to https://notebooklm.google.com
2. Create a new notebook
3. Click "Add source" → "Upload file"
4. Select `claude_conversations.md`
5. NotebookLM will analyze all your conversations

## Data Privacy

- All extraction happens locally in your browser
- No data is sent to external servers (except claude.ai itself)
- The script only reads what you have access to
- All files are saved locally on your machine

## License

MIT
