from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import time
from collections import defaultdict

app = Flask(__name__)
DB_NAME = 'books.db'

####### DB INIT ######
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                genre TEXT,
                year INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS authors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                country TEXT,
                birth_year INTEGER
            )
        ''')

###### ROUTES ######
@app.route('/', methods=['GET'])
def index():
    mode = request.args.get('mode', 'sql')
    search_author = request.args.get('author', '')
    search_genre = request.args.get('genre', '')
    search_year = request.args.get('year', '')
    sort_by = request.args.get('sort', '')
    page = int(request.args.get('page', 1))
    per_page = 400
    offset = (page - 1) * per_page

    books = []
    total_books = 0

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        if mode == 'sql':
            count_query = "SELECT COUNT(*) FROM books WHERE 1=1"
            count_params = []
            if search_author:
                count_query += " AND author LIKE ?"
                count_params.append(f"%{search_author}%")
            if search_genre:
                count_query += " AND genre LIKE ?"
                count_params.append(f"%{search_genre}%")
            if search_year:
                count_query += " AND year = ?"
                count_params.append(search_year)
            cursor.execute(count_query, count_params)
            total_books = cursor.fetchone()[0]

            query = "SELECT * FROM books WHERE 1=1"
            params = []
            if search_author:
                query += " AND author LIKE ?"
                params.append(f"%{search_author}%")
            if search_genre:
                query += " AND genre LIKE ?"
                params.append(f"%{search_genre}%")
            if search_year:
                query += " AND year = ?"
                params.append(search_year)

            if sort_by in ['title', 'author', 'year']:
                query += f" ORDER BY {sort_by}"

            query += " LIMIT ? OFFSET ?"
            params.extend([per_page, offset])

            cursor.execute(query, params)
            books = cursor.fetchall()

        else:
            cursor.execute("SELECT * FROM books")
            all_books = cursor.fetchall()

            filtered = all_books
            if search_author:
                filtered = [b for b in filtered if search_author.lower() in b[2].lower()]
            if search_genre:
                filtered = [b for b in filtered if search_genre.lower() in b[3].lower()]
            if search_year:
                filtered = [b for b in filtered if str(b[4]) == str(search_year)]

            if sort_by == 'title':
                filtered.sort(key=lambda b: b[1])
            elif sort_by == 'author':
                filtered.sort(key=lambda b: b[2])
            elif sort_by == 'year':
                filtered.sort(key=lambda b: b[4])

            total_books = len(filtered)
            books = filtered[offset:offset + per_page]

    total_pages = (total_books + per_page - 1) // per_page

    return render_template(
        'index.html',
        books=books,
        mode=mode,
        author=search_author,
        genre=search_genre,
        year=search_year,
        sort=sort_by,
        page=page,
        total_pages=total_pages
    )

@app.route('/statistics')
def statistics():
    mode = request.args.get('mode', 'sql')
    aggregation = request.args.get('aggregation', 'author')
    page = int(request.args.get('page', 1))
    per_page = 5000
    offset = (page - 1) * per_page

    stats = []
    total_items = 0

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        if mode == 'sql':
            if aggregation == 'author':
                cursor.execute("SELECT COUNT(DISTINCT author) FROM books")
            else:
                cursor.execute("SELECT COUNT(DISTINCT genre) FROM books")
            total_items = cursor.fetchone()[0]

            if aggregation == 'author':
                query = "SELECT author, COUNT(*) FROM books GROUP BY author LIMIT ? OFFSET ?"
            else:
                query = "SELECT genre, COUNT(*) FROM books GROUP BY genre LIMIT ? OFFSET ?"
            cursor.execute(query, (per_page, offset))
            stats = cursor.fetchall()
        else:
            cursor.execute("SELECT * FROM books")
            all_books = cursor.fetchall()
            counter = {}
            index = 2 if aggregation == 'author' else 3
            for book in all_books:
                key = book[index]
                counter[key] = counter.get(key, 0) + 1

            all_items = list(counter.items())
            total_items = len(all_items)
            stats = all_items[offset:offset + per_page]

    total_pages = (total_items + per_page - 1) // per_page

    return render_template(
        'statistics.html',
        stats=stats,
        mode=mode,
        aggregation=aggregation,
        page=page,
        total_pages=total_pages
    )


@app.route('/benchmark')
def benchmark():
    results = {}

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        start_sql = time.time()
        cursor.execute('''
            SELECT author, COUNT(*) as total_books
            FROM books
            WHERE genre IN ('Science Fiction', 'Fantasy', 'History','Drama')
            GROUP BY author
            HAVING total_books >= 0
            ORDER BY total_books DESC
            LIMIT 1000000
        ''')
        cursor.fetchall()
        end_sql = time.time()

        start_imp = time.time()
        cursor.execute("SELECT author, genre, year, title FROM books")
        all_books = cursor.fetchall()

        filtered = [
            b for b in all_books
            if b[1] in ('Science Fiction', 'Fantasy', 'History','Drama')
            and 1980 <= b[2] <= 2025
            and 'a' in b[3].lower()
        ]

        counter = {}
        for book in filtered:
            author = book[0]
            counter[author] = counter.get(author, 0) + 1

        
        top_authors = sorted(
            [(author, count) for author, count in counter.items() if count >= 1],
            key=lambda x: x[1],
            reverse=True
        )[:1000000]
        end_imp = time.time()

    results['sql'] = round(end_sql - start_sql, 5)
    results['imperative'] = round(end_imp - start_imp, 5)

    return render_template('benchmark.html', results=results)

@app.route('/add', methods=['GET', 'POST'])
def add_book():
    mode = request.args.get('mode', 'sql')
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        genre = request.form['genre']
        year = request.form['year']

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            if mode == 'sql':
                cursor.execute("INSERT INTO books (title, author, genre, year) VALUES (?, ?, ?, ?)",
                               (title, author, genre, year))
            else:
                new_book = (title, author, genre, year)
                books = [new_book]
                for book in books:
                    cursor.execute("INSERT INTO books (title, author, genre, year) VALUES (?, ?, ?, ?)", book)

        return redirect(url_for('index', mode=mode))
    return render_template('add_book.html', mode=mode)

@app.route('/edit/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    mode = request.args.get('mode', 'sql')
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        if request.method == 'POST':
            title = request.form['title']
            author = request.form['author']
            genre = request.form['genre']
            year = request.form['year']
            cursor.execute("UPDATE books SET title=?, author=?, genre=?, year=? WHERE id=?",
                           (title, author, genre, year, book_id))
            return redirect(url_for('index', mode=mode))
        cursor.execute("SELECT * FROM books WHERE id=?", (book_id,))
        book = cursor.fetchone()
    return render_template('edit_book.html', book=book, mode=mode)

@app.route('/delete/<int:book_id>')
def delete_book(book_id):
    mode = request.args.get('mode', 'sql')
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM books WHERE id=?", (book_id,))
    return redirect(url_for('index', mode=mode))



if __name__ == '__main__':
    init_db()
    app.run(debug=True)