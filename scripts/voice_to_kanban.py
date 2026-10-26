#!/usr/bin/env python3
"""Voice transcript -> Kanban task ingestion for Lemonade Stand.

Reads the daily voice transcripts in ~/hermes-archive/transcripts/, extracts
distinct tasks/deals/decisions/commitments from BOTH the user's spoken words
and the bot's replies, and creates them as Kanban board cards (sheet 'Kanban'
on the LMS data server). Deduped by normalized objective so nothing spoken is
ever lost and nothing is created twice.

Runs on the daily cron alongside the transcript archiver.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

TRANSCRIPTS = os.path.expanduser('~/hermes-archive/transcripts')
STATE_FILE = os.path.expanduser('~/hermes-archive/kanban_ingest_state.json')
API = 'http://127.0.0.1:8646/data'
API_KEY = 'lms-default-key-2026'
SHEET = 'Kanban'

# Task-like signals: commitment phrases and strong task verbs. Prefer explicit
# commitments ("I'll build", "we need to", "I want to") over bare verbs, which
# match too much conversational filler in assistant replies.
TASK_SIGNAL_RE = re.compile(
    r'\b(?:i\'ll|i will|i\'m going to|we need to|we should|we have to|'
    r'i want to|i need to|let\'s|lets|we\'ll|we will|'
    r'start|build|set up|create|make sure|reach out|follow up|follow-up|'
    r'close|sign|schedule|book|research|source|negotiate|draft|prepare|'
    r'launch|deploy|fix|finalize|execute|track|organize)\b',
    re.IGNORECASE,
)

# Bot/system markers that voice mode threads into transcript sections.
BOT_MARKERS = (
    '[hermes agent [bot]]', '[Replying to:', '•', '**', '⚠️', '⌛',
    'cd /home/ubuntu', 'open(p,', '```', 'Do you want Hermes',
    "If you don't answer",
)


def api_get(sheet):
    req = urllib.request.Request(f'{API}/{sheet}', headers={'X-API-Key': API_KEY})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read()).get('data', [])


def api_post(sheet, action, payload):
    body = json.dumps({'action': action, **payload}).encode()
    req = urllib.request.Request(f'{API}/{sheet}', data=body, method='POST',
                                 headers={'Content-Type': 'application/json', 'X-API-Key': API_KEY})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            return json.loads(open(STATE_FILE).read())
        except Exception:
            return {}
    return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def extract_tasks(text):
    """Split transcript into candidate task lines from USER and ASSISTANT turns.

    The transcript interleaves User and Assistant sections. Both the user's
    spoken words AND the bot's replies are task candidates — assistant replies
    often contain commitments, next steps, and decisions worth tracking.
    System/tool sections are never ingested.
    """
    candidates = []
    in_turn = False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('## User') or line.startswith('## Assistant'):
            in_turn = True
            continue
        if line.startswith('## Tool') or line.startswith('## Session_meta'):
            in_turn = False
            continue
        if not in_turn:
            continue
        if not line or len(line) < 12:
            continue
        # Skip headers, timestamps, metadata
        if line.startswith('#') or line.startswith('---') or line.startswith('Generated:') \
           or line.startswith('Sessions covered:'):
            continue
        # Skip bot/system markers
        if any(m in line for m in BOT_MARKERS):
            continue
        # Drop code references, numbered-list items, and shell commands (assistant output)
        if '`' in line or re.match(r'^\d+\.\s', line) or line.startswith('sudo ') \
           or line.startswith('cd ') or line.startswith('python3 ') or line.startswith('hermes '):
            continue
        # Drop short conversational fragments that aren't real tasks
        if len(line) < 30:
            continue
        if TASK_SIGNAL_RE.search(line):
            candidates.append(line)
    return candidates


def normalize(obj):
    """Normalize an objective for dedup: lowercase, strip punctuation, collapse spaces."""
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', obj.lower())).strip()


def main():
    if not os.path.isdir(TRANSCRIPTS):
        print('No transcripts dir:', TRANSCRIPTS)
        return

    state = load_state()
    processed = set(state.get('processed_files', []))
    created = 0
    skipped = 0

    # Existing board for dedup
    try:
        board = api_get(SHEET)
    except Exception as e:
        print(f'ERROR: could not reach LMS data server: {e}')
        sys.exit(1)
    existing_norms = {normalize(c.get('objective', '')) for c in board}

    files = sorted(f for f in os.listdir(TRANSCRIPTS) if f.endswith('.md'))
    for fname in files:
        if fname in processed:
            continue
        path = os.path.join(TRANSCRIPTS, fname)
        try:
            text = open(path).read()
        except Exception as e:
            print(f'  skip {fname}: {e}')
            continue

        tasks = extract_tasks(text)
        for task in tasks:
            norm = normalize(task)
            if not norm or norm in existing_norms:
                skipped += 1
                continue
            card = {
                'id': 'voice_' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S') + '_' + str(len(existing_norms) + created),
                'objective': task,
                'owner': '',
                'company': '',
                'acceptance_criteria': '',
                'state': 'todo',
                'dependencies': '',
                'notes': f'Source: voice transcript {fname}',
                'source': 'voice',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }
            try:
                api_post(SHEET, 'create', {'row': card})
                existing_norms.add(norm)
                created += 1
            except Exception as e:
                print(f'  ERROR creating task: {e}')

        processed.add(fname)

    state['processed_files'] = sorted(processed)
    state['last_run'] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    print(f'KANBAN INGEST: {created} created, {skipped} skipped (dup/not-task), {len(processed)} files processed')


if __name__ == '__main__':
    main()
