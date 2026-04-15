"""Extract readable text from a Claude Code JSONL transcript.

Usage: python extract_transcript.py <path_to_jsonl> [--max-chars N]

Outputs plain text with role-prefixed messages, suitable for wiki construction.
"""
import json
import sys
import argparse


def extract_messages(jsonl_path: str, max_chars: int = 200_000) -> str:
    messages = []
    total_chars = 0

    with open(jsonl_path) as f:
        for line in f:
            d = json.loads(line)
            if d["type"] not in ("user", "assistant"):
                continue

            msg = d.get("message", {})
            role = msg.get("role", d["type"])
            content = msg.get("content", "")

            if isinstance(content, list):
                parts = []
                for c in content:
                    if c.get("type") == "text":
                        parts.append(c["text"])
                    elif c.get("type") == "tool_use":
                        parts.append(f"[tool: {c.get('name', '?')}]")
                    elif c.get("type") == "tool_result":
                        text = c.get("content", "")
                        if isinstance(text, list):
                            text = " ".join(
                                t.get("text", "") for t in text if t.get("type") == "text"
                            )
                        if len(str(text)) > 500:
                            text = str(text)[:500] + "..."
                        parts.append(f"[tool_result: {text}]")
                text = "\n".join(parts)
            elif isinstance(content, str):
                text = content
            else:
                text = str(content)

            text = text.strip()
            if not text:
                continue

            entry = f"## {role}\n\n{text}\n"
            total_chars += len(entry)
            if total_chars > max_chars:
                messages.append(f"\n[TRUNCATED at {max_chars} chars — {len(messages)} messages shown]\n")
                break
            messages.append(entry)

    return "\n---\n\n".join(messages)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl_path")
    parser.add_argument("--max-chars", type=int, default=200_000)
    args = parser.parse_args()

    print(extract_messages(args.jsonl_path, args.max_chars))
