"""
NEXUS Memory Layer.
Handles session history, long-term persistence in JSON, and learned system rules.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import config

class Memory:
    """
    Manages short-term conversation context and long-term persistent learnings.
    """

    def __init__(self, memory_dir: Optional[Path] = None):
        self.memory_dir = memory_dir or config.MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.conversation_file = self.memory_dir / "conversation_log.json"
        self.rules_file = self.memory_dir / "learned_rules.json"

        self.history: List[Dict[str, Any]] = []
        self.rules: List[str] = []

        self.load()

    def add_entry(self, role: str, content: str, agent: Optional[str] = None):
        """
        Record a conversation entry.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "agent": agent
        }
        self.history.append(entry)
        self.save()

    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Return the most recent N entries.
        """
        return self.history[-limit:] if limit > 0 else self.history

    def get_formatted_history(self, limit: int = 6) -> str:
        """
        Format recent conversation history as a text block for prompt injection.
        """
        recent = self.get_recent(limit)
        if not recent:
            return ""

        formatted_lines = []
        for item in recent:
            role = item.get("role", "user")
            agent = f" ({item['agent']})" if item.get("agent") else ""
            formatted_lines.append(f"{role.capitalize()}{agent}: {item.get('content', '')}")
        return "\n".join(formatted_lines)

    def learn_rule(self, rule: str):
        """
        Save a persistent guideline or rule learned from user feedback.
        """
        cleaned = rule.strip()
        if cleaned and cleaned not in self.rules:
            self.rules.append(cleaned)
            self.save_rules()

    def get_learned_rules(self) -> List[str]:
        """
        Get all active persistent rules.
        """
        return list(self.rules)

    def get_rules_prompt(self) -> str:
        """
        Format rules for prompt context.
        """
        if not self.rules:
            return ""
        rules_text = "\n".join(f"- {r}" for r in self.rules)
        return f"Persistent Rules & Learnings:\n{rules_text}"

    def save(self):
        """
        Save conversation history to disk.
        """
        try:
            with open(self.conversation_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[⚠️ Memory Error saving conversation]: {e}")

    def save_rules(self):
        """
        Save learned rules to disk.
        """
        try:
            with open(self.rules_file, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[⚠️ Memory Error saving rules]: {e}")

    def load(self):
        """
        Load conversation history and rules from disk.
        """
        if self.conversation_file.exists():
            try:
                with open(self.conversation_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.history = data
            except Exception:
                self.history = []
        else:
            self.history = []

        if self.rules_file.exists():
            try:
                with open(self.rules_file, "r", encoding="utf-8") as f:
                    rules_data = json.load(f)
                    if isinstance(rules_data, list):
                        self.rules = rules_data
            except Exception:
                self.rules = []
        else:
            self.rules = []

    def clear(self):
        """
        Clear in-memory and disk conversation history (rules are preserved).
        """
        self.history.clear()
        self.save()

    def __len__(self) -> int:
        return len(self.history)

    def __iter__(self):
        return iter(self.history)
