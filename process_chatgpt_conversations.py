#!/usr/bin/env python3
"""
ChatGPT Conversations JSON to Markdown Converter
Properly parses ChatGPT's hierarchical message structure and extracts full conversations
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def traverse_messages(mapping, node_id, messages_list):
    """Recursively traverse the message tree structure"""
    if node_id not in mapping:
        return

    node = mapping[node_id]

    # Extract message if it exists
    if 'message' in node and node['message'] is not None:
        message = node['message']
        author = message.get('author', {}).get('role', 'unknown')

        # Extract content
        content = message.get('content', {})
        text = ""

        if isinstance(content, dict):
            parts = content.get('parts', [])
            if isinstance(parts, list):
                text = '\n'.join(str(p) for p in parts if p)

        if text:
            messages_list.append({
                'role': author,
                'text': text,
                'timestamp': message.get('create_time')
            })

    # Process children nodes
    children = node.get('children', [])
    for child_id in children:
        traverse_messages(mapping, child_id, messages_list)

def extract_conversations(json_file):
    """Load and extract conversations from JSON"""
    print(f"Loading {json_file}...")

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return []

    if not isinstance(data, list):
        print("Warning: JSON is not a list, attempting to extract conversations...")
        if isinstance(data, dict):
            data = [data]

    conversations = []
    print(f"Processing {len(data)} conversations...\n")

    for idx, conv in enumerate(data, 1):
        if idx % 100 == 0:
            print(f"  Processed {idx}/{len(data)} conversations...")

        title = conv.get('title', 'Untitled')
        create_time = conv.get('create_time')
        mapping = conv.get('mapping', {})

        # Find root message (usually has no parent)
        messages = []
        for node_id, node in mapping.items():
            if 'parent' not in node or node.get('parent') is None:
                # This is a root node, start traversal here
                traverse_messages(mapping, node_id, messages)

        if messages:
            conversations.append({
                'title': title,
                'created_at': create_time,
                'messages': messages
            })

    return conversations

def group_by_month(conversations):
    """Group conversations by month"""
    by_month = defaultdict(list)

    for conv in conversations:
        if conv['created_at']:
            # Convert timestamp to date string
            try:
                dt = datetime.fromtimestamp(conv['created_at'])
                month_key = dt.strftime('%Y-%m')
            except:
                month_key = 'undated'
        else:
            month_key = 'undated'

        by_month[month_key].append(conv)

    return dict(sorted(by_month.items()))

def create_markdown_files(conversations_by_month, output_dir):
    """Create markdown files organized by month"""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    print(f"\nCreating markdown files in {output_dir}...\n")

    for month, convs in conversations_by_month.items():
        filename = f"chatgpt_conversations_{month}.md"
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# ChatGPT Conversations - {month}\n\n")
            f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write(f"**Total conversations: {len(convs)}**\n\n")
            f.write("---\n\n")

            for i, conv in enumerate(convs, 1):
                title = conv['title']
                messages = conv['messages']
                created = datetime.fromtimestamp(conv['created_at']).isoformat() if conv['created_at'] else 'Unknown'

                f.write(f"## {i}. {title}\n\n")
                f.write(f"**Created:** {created}\n")
                f.write(f"**Messages:** {len(messages)}\n\n")

                # Write conversation
                for msg in messages:
                    role = msg['role'].upper()
                    text = msg['text']
                    f.write(f"**{role}:**\n{text}\n\n")

                f.write("---\n\n")

        print(f"✓ {filename} ({len(convs)} conversations, {filepath.stat().st_size / 1024:.1f} KB)")

    print(f"\n✓ All files saved to {output_dir}/")

def main():
    parser = argparse.ArgumentParser(description='Convert ChatGPT conversations.json to markdown files')
    parser.add_argument('--input', required=True, help='Path to conversations.json file')
    parser.add_argument('--output', default='./chatgpt_export', help='Output directory for markdown files')

    args = parser.parse_args()

    json_file = Path(args.input)

    if not json_file.exists():
        print(f"Error: File not found: {json_file}")
        return

    print("=" * 70)
    print("ChatGPT Conversations Converter")
    print("=" * 70)

    # Extract conversations
    conversations = extract_conversations(json_file)

    if not conversations:
        print("No conversations found!")
        return

    print(f"\n✓ Successfully extracted {len(conversations)} conversations with content\n")

    # Group by month
    by_month = group_by_month(conversations)

    print(f"Organized into {len(by_month)} months:")
    for month in by_month:
        print(f"  - {month}: {len(by_month[month])} conversations")

    # Create markdown files
    create_markdown_files(by_month, args.output)

if __name__ == '__main__':
    main()
