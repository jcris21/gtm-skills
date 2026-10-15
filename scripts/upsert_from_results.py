import json
import glob
import subprocess
import datetime
import os

"""
Script to upsert drafts from result JSON files into Google Sheet via utils/sheet_queue.py.
Reads each JSON in the results directory and, for each lead, calls:

  python utils/sheet_queue.py upsert-draft \
    --lead-id <lead_id> \
    --canal email|linkedin \
    --draft "<draft>" \
    --metadata-json '<full JSON object>' \
    --timestamp-draft <ISO timestamp>

Ensure utils/sheet_queue.py is in your PATH or adjust the path accordingly.
"""

# Directory containing result JSONs
results_dir = os.path.join('batches', 'batch-2026-09-27-batch1', 'results')

# Current UTC timestamp for drafts
timestamp = datetime.datetime.utcnow().isoformat() + '+00:00'

for json_path in glob.glob(os.path.join(results_dir, '*.json')):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    lead_id = data.get('lead_id')
    if not lead_id:
        continue

    # Upsert for email draft if drafted
    if data.get('email_drafted', False):
        draft = data.get('draft_email', '') or ''
        metadata = json.dumps(data, ensure_ascii=False)
        cmd = [
            'python', 'utils/sheet_queue.py', 'upsert-draft',
            '--lead-id', lead_id,
            '--canal', 'email',
            '--draft', draft,
            '--metadata-json', metadata,
            '--timestamp-draft', timestamp
        ]
        print('Upserting email draft for', lead_id)
        subprocess.run(cmd, check=True)

    # Upsert for LinkedIn draft if drafted
    if data.get('linkedin_drafted', False):
        draft = data.get('draft_linkedin', '') or ''
        metadata = json.dumps(data, ensure_ascii=False)
        cmd = [
            'python', 'utils/sheet_queue.py', 'upsert-draft',
            '--lead-id', lead_id,
            '--canal', 'linkedin',
            '--draft', draft,
            '--metadata-json', metadata,
            '--timestamp-draft', timestamp
        ]
        print('Upserting LinkedIn draft for', lead_id)
        subprocess.run(cmd, check=True)

print('✅ All drafts upserted to the Sheet.')