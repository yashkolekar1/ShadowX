"""Seed the MongoDB database with language-specific challenges, MCQs, puzzles, and peer questions.
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
peer_questions = db.peer_questions

sample_data = {
    'Python': {
        'challenges': [
            {
                'title': 'List Comprehension Filtering & Mapping',
                'description': 'Given a list of integers, write a function that returns a new list containing the squares of only the even numbers, in reverse order.',
                'topic': 'Python',
                'difficulty': 'Easy',
                'sample_input': '[1, 2, 3, 4, 5, 6]',
                'sample_output': '[36, 16, 4]'
            },
            {
                'title': 'Custom Memoization Decorator',
                'description': 'Create a Python decorator `@memoize` that caches the return values of expensive recursive function calls like Fibonacci calculation.',
                'topic': 'Python',
                'difficulty': 'Medium',
                'sample_input': 'fib(10)',
                'sample_output': '55 (with cached execution speedup)'
            },
            {
                'title': 'Context Manager for File Locking',
                'description': 'Implement a custom context manager `class FileLock` using Python\'s `__enter__` and `__exit__` methods to simulate file access locking.',
                'topic': 'Python',
                'difficulty': 'Hard',
                'sample_input': 'with FileLock("file.txt"): pass',
                'sample_output': 'Lock acquired -> file processed -> Lock released'
            }
        ],
        'mcqs': [
            {
                'question': 'What is the output of `list(range(0, 10, 2))` in Python?',
                'options': ['[0, 2, 4, 6, 8]', '[0, 2, 4, 6, 8, 10]', '[2, 4, 6, 8]', '(0, 2, 4, 6, 8)'],
                'correct_answer': '[0, 2, 4, 6, 8]',
                'topic': 'Python'
            },
            {
                'question': 'Which keyword is used to define a generator function in Python?',
                'options': ['yield', 'return', 'generator', 'defgen'],
                'correct_answer': 'yield',
                'topic': 'Python'
            },
            {
                'question': 'Which built-in Python data structure is ordered, mutable, and allows duplicate elements?',
                'options': ['list', 'tuple', 'set', 'dict'],
                'correct_answer': 'list',
                'topic': 'Python'
            },
            {
                'question': 'How do you perform integer (floor) division in Python?',
                'options': ['//', '/', '%', 'div()'],
                'correct_answer': '//',
                'topic': 'Python'
            },
            {
                'question': 'What does `*args` pass to a Python function?',
                'options': ['A variable number of positional arguments as a tuple', 'A variable number of keyword arguments as a dictionary', 'A list of pointers', 'A pointer array'],
                'correct_answer': 'A variable number of positional arguments as a tuple',
                'topic': 'Python'
            }
        ],
        'puzzles': [
            {
                'question': 'I am a special double-underscore method in Python called when an object is initialized. What am I?',
                'answer': '__init__'
            },
            {
                'question': 'Which built-in Python function takes an iterable and yields pairs of (index, item)?',
                'answer': 'enumerate'
            },
            {
                'question': 'I convert an object to a string for debugging purposes in Python, starting with double underscores. What method am I?',
                'answer': '__repr__'
            }
        ]
    },
    'JavaScript': {
        'challenges': [
            {
                'title': 'Debounce Function Implementation',
                'description': 'Write a higher-order `debounce(fn, delay)` function in JavaScript to delay function execution until after specified milliseconds have elapsed since last call.',
                'topic': 'JavaScript',
                'difficulty': 'Medium',
                'sample_input': 'const debouncedFn = debounce(search, 300);',
                'sample_output': 'Executes search only after user stops typing for 300ms'
            },
            {
                'title': 'Deep Clone Object',
                'description': 'Write a function `deepClone(obj)` that creates a deep copy of a nested JavaScript object without using JSON.parse(JSON.stringify(obj)).',
                'topic': 'JavaScript',
                'difficulty': 'Hard',
                'sample_input': '{ a: 1, b: { c: 2 } }',
                'sample_output': 'Independent copy with unique nested memory references'
            },
            {
                'title': 'Array Flattening Utility',
                'description': 'Write a recursive function `flattenArray(arr)` to flatten deeply nested arrays into a single-level array.',
                'topic': 'JavaScript',
                'difficulty': 'Easy',
                'sample_input': '[1, [2, [3, 4], 5]]',
                'sample_output': '[1, 2, 3, 4, 5]'
            }
        ],
        'mcqs': [
            {
                'question': 'What is the evaluation of `0 == "0"` and `0 === "0"` in JavaScript?',
                'options': ['true, false', 'false, true', 'true, true', 'false, false'],
                'correct_answer': 'true, false',
                'topic': 'JavaScript'
            },
            {
                'question': 'Which array method tests whether all elements in the array pass the provided test function?',
                'options': ['every()', 'some()', 'filter()', 'map()'],
                'correct_answer': 'every()',
                'topic': 'JavaScript'
            },
            {
                'question': 'What concept allows inner functions to retain access to variables from an outer scope after outer function returns?',
                'options': ['Closure', 'Hoisting', 'Prototype inheritance', 'Event loop'],
                'correct_answer': 'Closure',
                'topic': 'JavaScript'
            },
            {
                'question': 'Which keyword declares a block-scoped variable that cannot be reassigned?',
                'options': ['const', 'let', 'var', 'static'],
                'correct_answer': 'const',
                'topic': 'JavaScript'
            },
            {
                'question': 'What does `Promise.all()` return when one of the promises rejects?',
                'options': ['Immediately rejects with the error of the first rejected promise', 'Resolves with an array containing the errors', 'Waits for all promises regardless', 'Returns undefined'],
                'correct_answer': 'Immediately rejects with the error of the first rejected promise',
                'topic': 'JavaScript'
            }
        ],
        'puzzles': [
            {
                'question': 'What keyword in JavaScript refers to the object from which a function was invoked?',
                'answer': 'this'
            },
            {
                'question': 'What will `typeof NaN` return in JavaScript?',
                'answer': 'number'
            },
            {
                'question': 'Which built-in object provides static methods for mathematical constants and calculations in JS?',
                'answer': 'Math'
            }
        ]
    },
    'Java': {
        'challenges': [
            {
                'title': 'Thread-Safe Singleton Pattern',
                'description': 'Implement a double-checked locking Thread-Safe Singleton class in Java using the `volatile` keyword.',
                'topic': 'Java',
                'difficulty': 'Medium',
                'sample_input': 'Singleton instance = Singleton.getInstance();',
                'sample_output': 'Single global thread-safe instance guaranteed'
            },
            {
                'title': 'LRU Cache Implementation',
                'description': 'Design and implement a Least Recently Used (LRU) Cache data structure using `HashMap` and a Doubly Linked List in Java.',
                'topic': 'Java',
                'difficulty': 'Hard',
                'sample_input': 'cache.put(1, 1); cache.get(1);',
                'sample_output': 'O(1) get and put operations with automatic eviction'
            }
        ],
        'mcqs': [
            {
                'question': 'Which keyword prevents a Java method from being overridden by subclasses?',
                'options': ['final', 'static', 'abstract', 'private'],
                'correct_answer': 'final',
                'topic': 'Java'
            },
            {
                'question': 'What is the default initial capacity of an `ArrayList` in Java when unspecified?',
                'options': ['10', '16', '8', '0'],
                'correct_answer': '10',
                'topic': 'Java'
            },
            {
                'question': 'Which exception is thrown when attempting to divide an integer by zero in Java?',
                'options': ['ArithmeticException', 'NullPointerException', 'IllegalArgumentException', 'DivideByZeroException'],
                'correct_answer': 'ArithmeticException',
                'topic': 'Java'
            },
            {
                'question': 'Which Interface does NOT extend the `Collection` root interface in Java?',
                'options': ['Map', 'List', 'Set', 'Queue'],
                'correct_answer': 'Map',
                'topic': 'Java'
            }
        ],
        'puzzles': [
            {
                'question': 'Which keyword is used in Java to explicitly invoke a superclass constructor?',
                'answer': 'super'
            },
            {
                'question': 'Which Java memory area stores object instances and class data at runtime?',
                'answer': 'Heap'
            }
        ]
    },
    'C++': {
        'challenges': [
            {
                'title': 'Custom Smart Pointer (unique_ptr)',
                'description': 'Implement a simple template class `SmartPtr<T>` in C++ that manages raw pointer memory via RAII principles (destructor automatic deletion).',
                'topic': 'C++',
                'difficulty': 'Hard',
                'sample_input': 'SmartPtr<int> ptr(new int(42));',
                'sample_output': 'Deallocates memory automatically on scope exit'
            },
            {
                'title': 'Custom Vector Class',
                'description': 'Implement a dynamic array class `MyVector` supporting `push_back`, dynamic capacity doubling, and element index operator `[]`.',
                'topic': 'C++',
                'difficulty': 'Medium',
                'sample_input': 'MyVector v; v.push_back(10);',
                'sample_output': 'Resizes buffer dynamically when capacity is reached'
            }
        ],
        'mcqs': [
            {
                'question': 'What is the difference between `delete` and `delete[]` in C++?',
                'options': ['delete frees single object memory; delete[] frees dynamically allocated array memory', 'They are completely interchangeable', 'delete[] is used for pointers to pointers', 'delete is for stack memory; delete[] is for heap memory'],
                'correct_answer': 'delete frees single object memory; delete[] frees dynamically allocated array memory',
                'topic': 'C++'
            },
            {
                'question': 'Which pointer type introduced in C++11 represents shared ownership of dynamic objects?',
                'options': ['std::shared_ptr', 'std::unique_ptr', 'std::weak_ptr', 'auto_ptr'],
                'correct_answer': 'std::shared_ptr',
                'topic': 'C++'
            },
            {
                'question': 'What is the default access specifier for members of a `struct` in C++?',
                'options': ['public', 'private', 'protected', 'internal'],
                'correct_answer': 'public',
                'topic': 'C++'
            }
        ],
        'puzzles': [
            {
                'question': 'What macro/keyword prevents standard C++ headers from being included multiple times?',
                'answer': '#pragma once'
            },
            {
                'question': 'Which operator is overloaded to enable customized console output stream operations (`std::cout << obj`) in C++?',
                'answer': '<<'
            }
        ]
    },
    'DSA': {
        'challenges': [
            {
                'title': 'Detect Cycle in a Linked List',
                'description': 'Write an algorithm using Floyd\'s Cycle Detection algorithm (Fast & Slow Pointers) to determine if a singly linked list contains a cycle.',
                'topic': 'DSA',
                'difficulty': 'Medium',
                'sample_input': 'Head -> 1 -> 2 -> 3 -> 4 -> (points back to 2)',
                'sample_output': 'True (Cycle detected)'
            },
            {
                'title': 'Valid Parentheses Checker',
                'description': 'Using a Stack data structure, determine if a string containing characters `()[]{}` is balanced and valid.',
                'topic': 'DSA',
                'difficulty': 'Easy',
                'sample_input': '"({[]})"',
                'sample_output': 'True'
            },
            {
                'title': 'Binary Tree Lowest Common Ancestor',
                'description': 'Given a binary tree and two nodes p and q, find the lowest common ancestor (LCA) node in the tree.',
                'topic': 'DSA',
                'difficulty': 'Hard',
                'sample_input': 'Tree with nodes p=5, q=1',
                'sample_output': 'LCA node value = 3'
            }
        ],
        'mcqs': [
            {
                'question': 'What is the average time complexity of searching for an element in a Hash Table?',
                'options': ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)'],
                'correct_answer': 'O(1)',
                'topic': 'DSA'
            },
            {
                'question': 'Which data structure operates on a Last-In, First-Out (LIFO) order?',
                'options': ['Stack', 'Queue', 'Array', 'Linked List'],
                'correct_answer': 'Stack',
                'topic': 'DSA'
            },
            {
                'question': 'What is the worst-case time complexity of Quick Sort algorithm?',
                'options': ['O(n^2)', 'O(n log n)', 'O(n)', 'O(log n)'],
                'correct_answer': 'O(n^2)',
                'topic': 'DSA'
            },
            {
                'question': 'Which graph traversal algorithm uses a Queue data structure?',
                'options': ['Breadth-First Search (BFS)', 'Depth-First Search (DFS)', 'Dijkstra Algorithm', 'Kruskal Algorithm'],
                'correct_answer': 'Breadth-First Search (BFS)',
                'topic': 'DSA'
            }
        ],
        'puzzles': [
            {
                'question': 'What notation describes the upper bound of an algorithm\'s time complexity?',
                'answer': 'Big O'
            },
            {
                'question': 'I am a balanced binary search tree where the height difference between left and right subtrees is at most 1. What tree am I?',
                'answer': 'AVL Tree'
            }
        ]
    },
    'SQL': {
        'challenges': [
            {
                'title': 'Nth Highest Salary Query',
                'description': 'Write an SQL query to find the Nth highest salary from an `Employee` table without using vendor-specific LIMIT / OFFSET tricks.',
                'topic': 'SQL',
                'difficulty': 'Medium',
                'sample_input': 'Employee (id, salary)',
                'sample_output': 'Returns Nth highest distinct salary value'
            }
        ],
        'mcqs': [
            {
                'question': 'Which SQL clause is used to filter records resulting from an aggregate function like SUM() or COUNT()?',
                'options': ['HAVING', 'WHERE', 'GROUP BY', 'ORDER BY'],
                'correct_answer': 'HAVING',
                'topic': 'SQL'
            },
            {
                'question': 'Which JOIN returns all rows from the left table and matched rows from the right table?',
                'options': ['LEFT JOIN', 'INNER JOIN', 'RIGHT JOIN', 'FULL OUTER JOIN'],
                'correct_answer': 'LEFT JOIN',
                'topic': 'SQL'
            },
            {
                'question': 'Which constraint ensures that all values in a column are distinct and not null?',
                'options': ['PRIMARY KEY', 'UNIQUE', 'FOREIGN KEY', 'CHECK'],
                'correct_answer': 'PRIMARY KEY',
                'topic': 'SQL'
            }
        ],
        'puzzles': [
            {
                'question': 'Which SQL keyword removes duplicate rows from the result set of a SELECT query?',
                'answer': 'DISTINCT'
            }
        ]
    }
}

peer_questions_sample = [
    {
        'question': 'What is the real difference between process and thread in operating systems and how does Python GIL affect them?',
        'asked_by': 'AlexDev',
        'answers': [
            {
                'text': 'A process has its own isolated memory space, while threads within the same process share memory. In Python, the Global Interpreter Lock (GIL) permits only one thread to execute Python bytecode at a time, making multiprocessing better for CPU-bound tasks and multithreading ideal for I/O-bound tasks.',
                'answered_by': 'SeniorArchitect'
            }
        ]
    },
    {
        'question': 'When should I use SQL vs NoSQL (MongoDB) databases for a modern web app backend?',
        'asked_by': 'FullStackNewbie',
        'answers': [
            {
                'text': 'Use SQL when your data requires ACID transactional guarantees, strict relational schemas, and complex joins (e.g. financial systems). Use NoSQL (MongoDB) when dealing with flexible document schemas, horizontal scalability, rapid prototyping, or hierarchical JSON data.',
                'answered_by': 'DataLead'
            }
        ]
    },
    {
        'question': 'How does Async/Await work under the hood in JavaScript vs Python?',
        'asked_by': 'CodeExplorer',
        'answers': [
            {
                'text': 'Both use an Event Loop. In JS, Async functions return Promises, and `await` pauses execution of the async function until the promise settles. In Python, `asyncio` uses generators/coroutines scheduled on an event loop event queue.',
                'answered_by': 'PolyglotDev'
            }
        ]
    }
]

inserted = {'challenges': 0, 'mcqs': 0, 'puzzles': 0, 'peer_questions': 0}

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

# Peer Questions
for pq in peer_questions_sample:
    if not peer_questions.find_one({'question': pq['question']}):
        pq_doc = {
            'question': pq['question'],
            'asked_by': pq['asked_by'],
            'user_id': 'seeded_user',
            'created_at': datetime.utcnow(),
            'answers': [
                {
                    'text': ans['text'],
                    'answered_by': ans['answered_by'],
                    'user_id': 'expert_user',
                    'created_at': datetime.utcnow()
                } for ans in pq.get('answers', [])
            ]
        }
        peer_questions.insert_one(pq_doc)
        inserted['peer_questions'] += 1

# Seed Leaderboard Sample Users
sample_users = [
    {
        'username': 'Sarah_Conner',
        'email': 'sarah@shadowx.io',
        'role': 'user',
        'xp': 1450,
        'streak': 12,
        'solved_count': 34,
        'badges': ['Algorithm Master', 'Python Pioneer', 'Fast Learner'],
        'skill_python': 95,
        'skill_js': 88,
        'skill_dsa': 90,
        'created_at': datetime.utcnow()
    },
    {
        'username': 'DevGuru_Nikita',
        'email': 'nikita@shadowx.io',
        'role': 'user',
        'xp': 1180,
        'streak': 8,
        'solved_count': 27,
        'badges': ['Bug Hunter', 'Code Warrior', 'SQL Ninja'],
        'skill_python': 85,
        'skill_js': 92,
        'skill_dsa': 80,
        'created_at': datetime.utcnow()
    },
    {
        'username': 'Arjun_Codes',
        'email': 'arjun@shadowx.io',
        'role': 'user',
        'xp': 920,
        'streak': 5,
        'solved_count': 19,
        'badges': ['Puzzle Wizard', 'Fast Learner'],
        'skill_python': 80,
        'skill_js': 75,
        'skill_dsa': 78,
        'created_at': datetime.utcnow()
    }
]

users_col = db.users
for u in sample_users:
    if not users_col.find_one({'username': u['username']}):
        users_col.insert_one(u)

print(f"Inserted: {inserted}")
print("Seeding complete successfully.")
