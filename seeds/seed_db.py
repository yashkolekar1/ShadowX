"""Seed the MongoDB database with language-specific challenges, MCQs, and puzzles.
Run with: python seeds/seed_db.py
"""
from pymongo import MongoClient
from datetime import datetime
import os

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.environ.get('DB_NAME', 'shadowx_db')

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

challenges = db.challenges
mcqs = db.mcqs
puzzles = db.puzzles

sample_data = {
    'Python': {
        'challenges': [
            {
                'title': 'List Comprehension Practice',
                'description': 'Given a list of numbers, return a list of squares for even numbers only.',
                'topic': 'Python',
                'difficulty': 'Easy'
            },
            {
                'title': 'Decorator Basics',
                'description': 'Write a decorator that logs function call time and arguments.',
                'topic': 'Python',
                'difficulty': 'Medium'
            }
        ],
        'mcqs': [
            {
                'question': 'What is the output of: list(range(0,5))?',
                'options': ['[0, 1, 2, 3, 4]', '[1, 2, 3, 4, 5]', '(0,1,2,3,4)', 'range(0,5)'],
                'correct_answer': '[0, 1, 2, 3, 4]',
                'topic': 'Python'
            },
            {
                'question': 'Which keyword is used to define a function in Python?',
                'options': ['func', 'def', 'function', 'lambda'],
                'correct_answer': 'def',
                'topic': 'Python'
            },
            {
                'question': 'Which data type is immutable?',
                'options': ['list', 'dict', 'set', 'tuple'],
                'correct_answer': 'tuple',
                'topic': 'Python'
            }
        ],
        'puzzles': [
            {
                'question': 'I start with a capital letter and am used to create classes in Python. What am I?',
                'answer': 'ClassName'
            },
            {
                'question': 'Which built-in function returns the length of an object in Python?',
                'answer': 'len'
            }
        ]
    },
    'JavaScript': {
        'challenges': [
            {
                'title': 'Array Map/Filter Practice',
                'description': 'Use map and filter to transform an array of objects.',
                'topic': 'JavaScript',
                'difficulty': 'Easy'
            },
            {
                'title': 'Promise Chaining',
                'description': 'Chain multiple promises and handle errors properly.',
                'topic': 'JavaScript',
                'difficulty': 'Medium'
            }
        ],
        'mcqs': [
            {
                'question': 'Which company developed JavaScript?',
                'options': ['Microsoft', 'Netscape', 'Sun Microsystems', 'Oracle'],
                'correct_answer': 'Netscape',
                'topic': 'JavaScript'
            },
            {
                'question': 'Which of these is NOT a JavaScript data type?',
                'options': ['Number', 'String', 'Boolean', 'Character'],
                'correct_answer': 'Character',
                'topic': 'JavaScript'
            },
            {
                'question': 'What is the keyword to declare a variable with block scope?',
                'options': ['var', 'let', 'const', 'both let and const'],
                'correct_answer': 'both let and const',
                'topic': 'JavaScript'
            }
        ],
        'puzzles': [
            {
                'question': 'What will `typeof null` return in JavaScript?',
                'answer': 'object'
            },
            {
                'question': 'Which method converts a JSON string into a JavaScript object?',
                'answer': 'JSON.parse'
            }
        ]
    },
    'Java': {
        'challenges': [
            {
                'title': 'OOP Design Problem',
                'description': 'Design a simple class hierarchy for Vehicles and implement polymorphism.',
                'topic': 'Java',
                'difficulty': 'Medium'
            },
            {
                'title': 'Collections Practice',
                'description': 'Use Lists and Maps to aggregate data efficiently.',
                'topic': 'Java',
                'difficulty': 'Easy'
            }
        ],
        'mcqs': [
            {
                'question': 'Which keyword is used to inherit a class in Java?',
                'options': ['implements', 'extends', 'inherits', 'super'],
                'correct_answer': 'extends',
                'topic': 'Java'
            },
            {
                'question': 'Which of these is not a primitive type in Java?',
                'options': ['int', 'boolean', 'String', 'double'],
                'correct_answer': 'String',
                'topic': 'Java'
            },
            {
                'question': 'Which package contains the ArrayList class?',
                'options': ['java.util', 'java.lang', 'java.io', 'java.net'],
                'correct_answer': 'java.util',
                'topic': 'Java'
            }
        ],
        'puzzles': [
            {
                'question': 'What keyword is used to create a new object instance in Java?',
                'answer': 'new'
            },
            {
                'question': 'Which method is the entry point of a Java application?',
                'answer': 'public static void main(String[] args)'
            }
        ]
    },
    'C++': {
        'challenges': [
            {
                'title': 'Pointer Basics',
                'description': 'Manipulate pointers and dynamic memory safely.',
                'topic': 'C++',
                'difficulty': 'Medium'
            },
            {
                'title': 'STL Practice',
                'description': 'Use vectors and maps from the STL to solve a problem.',
                'topic': 'C++',
                'difficulty': 'Easy'
            }
        ],
        'mcqs': [
            {
                'question': 'Which header is needed for std::vector?',
                'options': ['<vector>', '<array>', '<list>', '<map>'],
                'correct_answer': '<vector>',
                'topic': 'C++'
            },
            {
                'question': 'What does RAII stand for?',
                'options': ['Resource Acquisition Is Initialization', 'Random Access Is Immediate', 'Resource Allocation In Initialization', 'None of the above'],
                'correct_answer': 'Resource Acquisition Is Initialization',
                'topic': 'C++'
            },
            {
                'question': 'Which operator is used for scope resolution?',
                'options': ['::', '->', '.', ':'],
                'correct_answer': '::',
                'topic': 'C++'
            }
        ],
        'puzzles': [
            {
                'question': 'Which C++ feature helps manage resource lifetime automatically?',
                'answer': 'RAII'
            },
            {
                'question': 'Which symbol is used to access members of a class via a pointer?',
                'answer': '->'
            }
        ]
    }
}

inserted = {'challenges': 0, 'mcqs': 0, 'puzzles': 0}

for lang, data in sample_data.items():
    # Challenges
    for ch in data.get('challenges', []):
        ch_doc = ch.copy()
        ch_doc['created_at'] = datetime.utcnow()
        ch_doc['topic'] = lang
        if not challenges.find_one({'title': ch_doc['title'], 'topic': lang}):
            challenges.insert_one(ch_doc)
            inserted['challenges'] += 1

    # MCQs
    for m in data.get('mcqs', []):
        m_doc = m.copy()
        m_doc['created_at'] = datetime.utcnow()
        m_doc['topic'] = lang
        if not mcqs.find_one({'question': m_doc['question'], 'topic': lang}):
            mcqs.insert_one(m_doc)
            inserted['mcqs'] += 1

    # Puzzles
    for p in data.get('puzzles', []):
        p_doc = {'question': p['question'], 'correct_answer': p['answer'], 'created_at': datetime.utcnow(), 'topic': lang}
        if not puzzles.find_one({'question': p_doc['question'], 'topic': lang}):
            puzzles.insert_one(p_doc)
            inserted['puzzles'] += 1

print(f"Inserted: {inserted}")
print("Seeding complete.")
