#!/usr/bin/env python3
"""
Convert Claude conversations.json to NotebookLM-compatible markdown.
Chunks by date and extracts full conversation context.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import zipfile
import argparse

class ClaudeToNotebookLM:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.conversations = []
        self.chunks = defaultdict(list)
        self.log_file = self.output_dir / "conversion.log"
    
    def _log(self, message: str):
        """Log to console and file."""
        print(message)
        with open(self.log_file, 'a') as f:
            f.write(message + "\n")
    
    def load_from_zip(self, zip_path: str) -> bool:
        """Extract and load conversations.json from zip."""
        self._log(f"[*] Opening zip: {zip_path}")
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                # Find conversations.json
                conv_file = None
                for name in z.namelist():
                    if name.endswith('conversations.json'):
                        conv_file = name
                        break
                
                if not conv_file:
                    self._log("[ERROR] conversations.json not found in zip")
                    return False
                
                self._log(f"[*] Found {conv_file}")
                
                # Read and parse
                with z.open(conv_file) as f:
                    self._log("[*] Loading conversations...")
                    self.conversations = json.load(f)
                    self._log(f"[OK] Loaded {len(self.conversations)} conversations")
                    return True
        
        except Exception as e:
            self._log(f"[ERROR] Failed to load zip: {e}")
            return False
    
    def load_from_file(self, json_path: str) -> bool:
        """Load conversations.json directly."""
        self._log(f"[*] Loading {json_path}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.conversations = json.load(f)
                self._log(f"[OK] Loaded {len(self.conversations)} conversations")
                return True
        except Exception as e:
            self._log(f"[ERROR] Failed to load JSON: {e}")
            return False
    
    def organize_by_chunks(self, chunk_type: str = 'month', chunk_size: int = 500):
        """Organize conversations into chunks for processing."""
        self._log(f"\n[*] Organizing {len(self.conversations)} conversations by {chunk_type}...")
        
        for conv in self.conversations:
            # Get creation timestamp
            create_time = conv.get('create_time', 0)
            
            if chunk_type == 'month':
                try:
                    dt = datetime.fromtimestamp(create_time)
                    chunk_key = dt.strftime('%Y-%m')
                except:
                    chunk_key = 'unknown'
            else:
                # Chunk by size
                chunk_num = len(self.chunks) // chunk_size
                chunk_key = f'batch-{chunk_num:03d}'
            
            self.chunks[chunk_key].append(conv)
        
        self._log(f"[OK] Created {len(self.chunks)} chunks:")
        for chunk_name in sorted(self.chunks.keys()):
            self._log(f"     {chunk_name}: {len(self.chunks[chunk_name])} conversations")
    
    def extract_message_content(self, content) -> str:
        """Extract text content from various message formats."""
        if isinstance(content, str):
            return content
        elif isinstance(content, dict):
            parts = content.get('parts', [])
            return ' '.join([str(p) for p in parts if p])
        elif isinstance(content, list):
            return ' '.join([str(p) for p in content if p])
        return str(content)
    
    def convert_chunk_to_markdown(self, conversations: list, chunk_name: str) -> str:
        """Convert a chunk of conversations to markdown."""
        lines = []
        lines.append(f"# Claude Conversations - {chunk_name}\n")
        lines.append(f"*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        lines.append(f"**Total: {len(conversations)} conversations**\n")
        lines.append("---\n\n")
        
        for i, conv in enumerate(conversations, 1):
            # Title
            title = conv.get('title', f'Conversation {i}')
            lines.append(f"## {i}. {title}\n\n")
            
            # Metadata
            create_time = conv.get('create_time', 0)
            if create_time:
                try:
                    dt = datetime.fromtimestamp(create_time)
                    lines.append(f"**Date:** {dt.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                except:
                    pass
            
            # Model info
            model = conv.get('model') or conv.get('model_slug', 'Unknown')
            lines.append(f"**Model:** {model}\n\n")
            
            # Messages
            messages = conv.get('messages', {})
            
            # Messages can be a list or dict depending on export format
            if isinstance(messages, dict):
                messages = list(messages.values())
            
            message_count = 0
            for msg in messages:
                if not msg:
                    continue
                
                # Extract role and author
                role = msg.get('role', 'unknown').upper()
                author = msg.get('author', {})
                
                if isinstance(author, dict):
                    author_name = author.get('name', role)
                else:
                    author_name = role
                
                # Extract content
                content = msg.get('content', '')
                
                if isinstance(content, dict):
                    text = self.extract_message_content(content)
                elif isinstance(content, str):
                    text = content
                else:
                    text = str(content)
                
                if text.strip():
                    lines.append(f"**{author_name}:**\n\n")
                    lines.append(f"{text.strip()}\n\n")
                    message_count += 1
            
            lines.append(f"*({message_count} messages)*\n")
            lines.append("\n---\n\n")
        
        return ''.join(lines)
    
    def export_to_markdown(self) -> bool:
        """Export chunks to markdown files."""
        self._log(f"\n[*] Writing markdown files...\n")
        
        output_files = []
        total_size = 0
        
        for chunk_name in sorted(self.chunks.keys()):
            convs = self.chunks[chunk_name]
            markdown = self.convert_chunk_to_markdown(convs, chunk_name)
            
            # Safe filename
            safe_name = chunk_name.replace(':', '-').replace('/', '-')
            output_path = self.output_dir / f"claude_conversations_{safe_name}.md"
            
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown)
                
                size_mb = len(markdown) / (1024 ** 2)
                total_size += len(markdown)
                output_files.append((output_path, size_mb))
                self._log(f"   [OK] {output_path.name} ({size_mb:.2f} MB)")
            
            except Exception as e:
                self._log(f"   [ERROR] Failed to write {output_path}: {e}")
        
        self._log(f"\n[OK] Total size: {total_size / (1024**2):.2f} MB")
        return len(output_files) > 0
    
    def run(self, zip_path: str = None, json_path: str = None):
        """Execute full conversion pipeline."""
        self._log("="*70)
        self._log("Claude Conversations to NotebookLM Converter")
        self._log("="*70 + "\n")
        
        # Load conversations
        if zip_path:
            success = self.load_from_zip(zip_path)
        elif json_path:
            success = self.load_from_file(json_path)
        else:
            self._log("[ERROR] Must provide --zip or --json")
            return False
        
        if not success or not self.conversations:
            self._log("[ERROR] No conversations loaded")
            return False
        
        # Process
        self.organize_by_chunks(chunk_type='month')
        success = self.export_to_markdown()
        
        if success:
            self._log("\n" + "="*70)
            self._log("CONVERSION COMPLETE")
            self._log("="*70)
            self._log(f"\n[OUTPUT] Location: {self.output_dir}")
            self._log(f"\n[NEXT] Upload .md files to NotebookLM:")
            self._log(f"   https://notebooklm.google.com")
            self._log(f"   → Create notebook")
            self._log(f"   → Add source → Upload each .md file\n")
        
        return success


def main():
    parser = argparse.ArgumentParser(
        description="Convert Claude conversations.json to NotebookLM markdown"
    )
    
    parser.add_argument(
        '--zip',
        type=str,
        help='Path to Claude export zip file'
    )
    
    parser.add_argument(
        '--json',
        type=str,
        help='Path to conversations.json file'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='./claude_notebooklm_export',
        help='Output directory (default: ./claude_notebooklm_export)'
    )
    
    args = parser.parse_args()
    
    converter = ClaudeToNotebookLM(args.output)
    success = converter.run(zip_path=args.zip, json_path=args.json)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
