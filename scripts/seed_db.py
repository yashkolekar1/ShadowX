"""Seed the MongoDB database with language-specific challenges, MCQs, and puzzles.
Deletes previously seeded documents (seeded=True) and inserts new sample data.
Run: python scripts/seed_db.py
"""
from pymongo import MongoClient
from datetime import datetime

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "shadowx_db"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

challenges = db.challenges
mcqs = db.mcqs
puzzles = db.puzzles

# Remove previous seed data
challenges.delete_many({'seeded': True})
mcqs.delete_many({'seeded': True})
puzzles.delete_many({'seeded': True})

now = datetime.now()

languages = [
    'Python',
    'JavaScript',
    'Java',
    'C++'
]

sample_challenges = []
sample_mcqs = []
sample_puzzles = []

for lang in languages:
    # Add 3 challenges per language
    for i in range(1, 4):
        sample_challenges.append({
            'title': f'{lang} Challenge {i}',
            'description': f'A practical {lang} problem #{i} to solve.',
            'topic': lang,
            'language': lang,
            'difficulty': 'Easy' if i == 1 else 'Medium' if i == 2 else 'Hard',
            'created_at': now,
            'seeded': True
        })

    # Add 3 MCQs per language
    for i in range(1, 4):
        sample_mcqs.append({
            'question': f'What does this {lang} snippet do? ({i})',
            'options': ["Option A", "Option B", "Option C", "Option D"],
            'correct_answer': 'Option A',
            'topic': lang,
            'language': lang,
            'created_at': now,
            'seeded': True
        })

    # Add 2 puzzles per language
    for i in range(1, 3):
        sample_puzzles.append({
            'question': f'{lang} puzzle #{i}: Guess the output',
            'correct_answer': '42',
            'posted_by': 'seed',
            'language': lang,
            'created_at': now,
            'seeded': True
        })

if sample_challenges:
    challenges.insert_many(sample_challenges)
if sample_mcqs:
    mcqs.insert_many(sample_mcqs)
if sample_puzzles:
    puzzles.insert_many(sample_puzzles)

print('Seeding complete:')
print(f"  Challenges inserted: {len(sample_challenges)}")
print(f"  MCQs inserted: {len(sample_mcqs)}")
print(f"  Puzzles inserted: {len(sample_puzzles)}")

# Print per-language counts
for lang in languages:
    c_cnt = challenges.count_documents({'language': lang})
    m_cnt = mcqs.count_documents({'language': lang})
    p_cnt = puzzles.count_documents({'language': lang})
    print(f"  {lang}: challenges={c_cnt}, mcqs={m_cnt}, puzzles={p_cnt}")

client.close()
