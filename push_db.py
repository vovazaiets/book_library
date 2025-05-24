import sqlite3
import random
from faker import Faker

DB_NAME = 'books.db'
NUM_BOOKS = 150_000


GENRES = ['Science Fiction', 'Fantasy', 'Mystery', 'Non-fiction', 'Romance', 'Horror', 'Thriller', 'History', 'Biography', 'Poetry']

fake = Faker()

def insert_books():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        books = []
        for _ in range(NUM_BOOKS):
            title = fake.sentence(nb_words=4)
            author = fake.name()
            genre = random.choice(GENRES)
            year = random.randint(1950, 2025)
            books.append((title, author, genre, year))

        cursor.executemany("INSERT INTO books (title, author, genre, year) VALUES (?, ?, ?, ?)", books)
        conn.commit()

    print(f"✅ Успішно додано {NUM_BOOKS} книг до бази даних '{DB_NAME}'.")

if __name__ == "__main__":
    insert_books()
