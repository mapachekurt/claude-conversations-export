#!/usr/bin/env python3
"""
Claude.ai Conversation Exporter - Async Long-Running Task
Runs in Claude Code Web with browser automation.

Usage:
    python export_claude_conversations.py --output ./exports --headless false

Features:
    - Full conversation context extraction (not just titles)
    - Browser-based scraping of claude.ai
    - Markdown export for NotebookLM
    - Progress tracking and resumable state
    - Rate limiting to avoid server strain
"""

import json
import os
import sys
import asyncio
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import argparse

# Try to import playwright for browser automation
try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    print("[WARNING] Playwright not installed. Install with: pip install playwright")

class ClaudeConversationExporter:
    def __init__(self, output_dir: str = "./claude_exports", headless: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.headless = headless
        self.conversations: List[Dict] = []
        self.state_file = self.output_dir / "export_state.json"
        self.log_file = self.output_dir / "export.log"
        
        self._load_state()
    
    def _log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)
        
        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")
    
    def _load_state(self):
        """Load previous export state (for resuming)."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.conversations = state.get('conversations', [])
                    self._log(f"Loaded {len(self.conversations)} conversations from previous run")
            except Exception as e:
                self._log(f"Failed to load state: {e}", "WARNING")
    
    def _save_state(self):
        """Save current export state."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump({
                    'conversations': self.conversations,
                    'timestamp': datetime.now().isoformat(),
                    'count': len(self.conversations)
                }, f, indent=2)
        except Exception as e:
            self._log(f"Failed to save state: {e}", "ERROR")
    
    async def extract_conversations(self) -> bool:
        """Extract all conversations from claude.ai using browser automation."""
        if not HAS_PLAYWRIGHT:
            self._log("Playwright required. Install with: pip install playwright", "ERROR")
            return False
        
        self._log("Starting Claude.ai conversation extraction...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Navigate to claude.ai
                self._log("Navigating to claude.ai...")
                await page.goto("https://claude.ai", timeout=30000)
                
                # Wait for login or home page
                self._log("Waiting for page to load...")
                await asyncio.sleep(3)
                
                # Check if logged in
                is_logged_in = await self._check_logged_in(page)
                
                if not is_logged_in:
                    self._log("Not logged in. Manual login required in browser window.")
                    self._log("Please log in and then press any key to continue...")
                    input("[MANUAL] Log in to claude.ai and press Enter to continue...")
                
                # Wait for sidebar to load
                await page.wait_for_selector("[role='navigation']", timeout=10000)
                self._log("Sidebar loaded. Extracting conversations...")
                
                # Get all conversation items from sidebar
                conversation_items = await page.query_selector_all("a[href*='/chat/']")
                self._log(f"Found {len(conversation_items)} conversations in sidebar")
                
                # Extract conversation data
                for i, item in enumerate(conversation_items, 1):
                    if i % 10 == 0:
                        self._log(f"Processing conversation {i}/{len(conversation_items)}...")
                    
                    try:
                        # Get conversation title and link
                        title = await item.get_attribute("title")
                        href = await item.get_attribute("href")
                        
                        if href:
                            conv_id = href.split('/chat/')[-1] if '/chat/' in href else None
                            
                            if conv_id:
                                # Navigate to conversation
                                await page.goto(f"https://claude.ai/chat/{conv_id}", timeout=15000)
                                await asyncio.sleep(1)  # Wait for content to load
                                
                                # Extract full conversation content
                                messages = await self._extract_messages(page)
                                
                                conversation = {
                                    'id': conv_id,
                                    'title': title or f'Conversation {i}',
                                    'url': f"https://claude.ai/chat/{conv_id}",
                                    'messages': messages,
                                    'message_count': len(messages),
                                    'extracted_at': datetime.now().isoformat()
                                }
                                
                                self.conversations.append(conversation)
                                self._save_state()
                    
                    except Exception as e:
                        self._log(f"Error extracting conversation {i}: {e}", "WARNING")
                        continue
                
                self._log(f"Extraction complete. Total conversations: {len(self.conversations)}")
                return True
            
            except Exception as e:
                self._log(f"Browser automation error: {e}", "ERROR")
                return False
            
            finally:
                await browser.close()
    
    async def _check_logged_in(self, page: Page) -> bool:
        """Check if user is logged into Claude.ai."""
        try:
            # Check for user menu or home content
            user_element = await page.query_selector("[data-testid='user-menu']")
            return user_element is not None
        except:
            return False
    
    async def _extract_messages(self, page: Page) -> List[Dict]:
        """Extract all messages from current conversation page."""
        messages = []
        try:
            # Wait for messages to load
            await page.wait_for_selector("[role='main']", timeout=5000)
            
            # Get message containers
            message_elements = await page.query_selector_all("div[data-testid='message']")
            
            for msg_elem in message_elements:
                try:
                    # Extract role (user/assistant)
                    role_indicator = await msg_elem.query_selector("[data-role]")
                    role = "user"
                    if role_indicator:
                        role = await role_indicator.get_attribute("data-role")
                    
                    # Extract message text
                    text_content = await msg_elem.text_content()
                    
                    if text_content:
                        messages.append({
                            'role': role,
                            'content': text_content.strip(),
                            'timestamp': datetime.now().isoformat()
                        })
                except Exception as e:
                    continue
            
            return messages
        except Exception as e:
            self._log(f"Error extracting messages: {e}", "WARNING")
            return messages
    
    def export_to_markdown(self) -> bool:
        """Export conversations to markdown files (NotebookLM format)."""
        self._log(f"Exporting {len(self.conversations)} conversations to markdown...")
        
        if not self.conversations:
            self._log("No conversations to export", "WARNING")
            return False
        
        # Create markdown content
        markdown = []
        markdown.append("# Claude.ai Conversations Export\n\n")
        markdown.append(f"*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        markdown.append(f"**Total Conversations: {len(self.conversations)}**\n\n")
        markdown.append("---\n\n")
        
        for i, conv in enumerate(self.conversations, 1):
            title = conv.get('title', f'Conversation {i}')
            markdown.append(f"## {i}. {title}\n\n")
            
            if 'url' in conv:
                markdown.append(f"**Link:** {conv['url']}\n\n")
            
            if 'extracted_at' in conv:
                markdown.append(f"**Extracted:** {conv['extracted_at']}\n\n")
            
            markdown.append(f"**Message Count:** {conv.get('message_count', 0)}\n\n")
            
            # Add messages
            messages = conv.get('messages', [])
            if messages:
                for msg in messages:
                    role = msg.get('role', 'unknown').upper()
                    content = msg.get('content', '').strip()
                    
                    if content:
                        markdown.append(f"**{role}:**\n\n{content}\n\n")
            
            markdown.append("---\n\n")
        
        # Save markdown file
        output_file = self.output_dir / "claude_conversations.md"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(''.join(markdown))
            
            size_mb = output_file.stat().st_size / (1024 ** 2)
            self._log(f"Exported to: {output_file} ({size_mb:.1f} MB)")
            return True
        
        except Exception as e:
            self._log(f"Error writing markdown: {e}", "ERROR")
            return False
    
    def export_to_json(self) -> bool:
        """Export raw conversation data as JSON."""
        self._log("Exporting to JSON...")
        
        output_file = self.output_dir / "claude_conversations.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversations, f, indent=2)
            
            size_mb = output_file.stat().st_size / (1024 ** 2)
            self._log(f"Exported to: {output_file} ({size_mb:.1f} MB)")
            return True
        
        except Exception as e:
            self._log(f"Error writing JSON: {e}", "ERROR")
            return False
    
    async def run(self, export_formats: List[str] = ['markdown', 'json']):
        """Execute full export pipeline."""
        self._log("="*70)
        self._log("Claude.ai Conversation Exporter")
        self._log("="*70)
        
        # Extract conversations
        success = await self.extract_conversations()
        
        if not success or not self.conversations:
            self._log("Extraction failed or no conversations found", "ERROR")
            return False
        
        # Export to requested formats
        if 'markdown' in export_formats:
            self.export_to_markdown()
        
        if 'json' in export_formats:
            self.export_to_json()
        
        self._log("\n" + "="*70)
        self._log("EXPORT COMPLETE")
        self._log("="*70)
        self._log(f"Location: {self.output_dir}")
        self._log(f"Total conversations: {len(self.conversations)}")
        
        return True


async def main():
    parser = argparse.ArgumentParser(description="Export Claude.ai conversations")
    
    parser.add_argument(
        '--output',
        type=str,
        default='./claude_exports',
        help='Output directory for exports (default: ./claude_exports)'
    )
    
    parser.add_argument(
        '--headless',
        type=str,
        default='true',
        choices=['true', 'false'],
        help='Run browser headless or with GUI (default: true)'
    )
    
    parser.add_argument(
        '--formats',
        type=str,
        default='markdown,json',
        help='Export formats: markdown,json,both (default: markdown,json)'
    )
    
    args = parser.parse_args()
    
    exporter = ClaudeConversationExporter(
        output_dir=args.output,
        headless=args.headless.lower() == 'true'
    )
    
    formats = [f.strip() for f in args.formats.split(',')]
    success = await exporter.run(export_formats=formats)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    if not HAS_PLAYWRIGHT:
        print("Installing Playwright...")
        os.system("pip install playwright")
        os.system("playwright install")
    
    asyncio.run(main())
