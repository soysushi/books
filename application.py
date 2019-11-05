import os
import requests

from flask import Flask, session, request, render_template, flash, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine, func, or_, text
from sqlalchemy.orm import scoped_session, sessionmaker

from tempfile import mkdtemp

from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash


from helpers import apology, login_required, lookup, usd
from models import *

# Configure session to use filesystem
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'
db=SQLAlchemy()
db.init_app(app)


# default page where user can search for the books, login required
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        # Get the submission
        query = str(request.form.get("search").lower())
        # Search the database for matching or part matching string, isbn, title, or author
        try:
            book = Book.query.filter(or_(Book.isbn.ilike("%" + query +"%"), Book.title.ilike("%" + query +"%"), Book.author.ilike("%" + query +"%"))).all()
        except ValueError:
            return apology("Sorry, book doesnt not exist", 404)
        return render_template("results.html", book=book)

    else:
        return render_template("index.html")

@app.route("/book/<int:book_id>")
def book(book_id):
    # Make sure book exists
    book = Book.query.get(book_id)

    if book is None:
        return apology("Sorry, no such book", 400)
    #Get the information of the book
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "VLoaQxy03FsRL3aWqEc2cg", "isbns": book.isbn})
    data = res.json()
    review = Reviews.query.filter_by(book_id=book_id, user_id=session["user_id"]).all()
    if (review):
        reviews = book.reviews[0]
    else:
        reviews = False
    return render_template("bookpage.html", book=data['books'][0], info=book, reviews=reviews)

@app.route("/review/<int:book_id>", methods=["POST"])
def review(book_id):
    if request.method == "POST":
        r = int(request.form.get("rating"))
        c = request.form.get("comments")
        s = session["user_id"]
        print(r)
        book = Book.query.get(book_id)
        if book is None:
            return apology("why is book none?", 400)
        book.add_review(r, c, s)
        return redirect("/")
    else:
        return apology("Sorry, method not allowed", 405)

@app.route("/register", methods=["GET", "POST"])
def register():

    # Forget any user # id
    session.clear()
    # If someone is submitting something
    if request.method == "POST":
        # Check username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)
        # Check password was submitted
        if not request.form.get("password"):
            return apology("must provide password", 400)
        if not request.form.get("confirmation"):
            return apology("must provide confirmation", 400)
        # check password and confirmation match
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if password != confirmation:
            return apology("passwords do not match", 400)

        # Generate encyrpted/hashed password
        hash = generate_password_hash(password)
        username = request.form.get("username")
        # Store hashed password into database
        result = db.session.execute("INSERT INTO users (username, password) VALUES (:username, :password) RETURNING id", {"username":username, "password":hash})

        if not result:
            return apology("username already taken", 400)
        # log the user in
        session["user_id"] = result.first()[0]
        db.session.commit()

        # return to home
        return redirect("/")
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        username = request.form.get("username")
        rows = db.session.execute("SELECT * FROM users WHERE username = :username", {"username":username}).fetchone()


        # Ensure username exists and password is correct
        if not rows or not check_password_hash(rows["password"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        print(rows["password"])
        # Remember which user has logged in
        session["user_id"] = rows["id"]
        print(session["user_id"])

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/api/<string:isbn>")
def apiBook(isbn):
    book = Book.query.filter_by(isbn=isbn)
    if book is None:
        return apology("Sorry, no such book", 400)
    #Get the information of the book
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "VLoaQxy03FsRL3aWqEc2cg", "isbns": isbn})
    data = res.json()
    goodreads_reviews = data['books'][0]
    print (goodreads_reviews)

    return jsonify({
        "title": book[0].title,
        "author": book[0].author,
        "year": book[0].year,
        "isbn": book[0].isbn,
        "review_count": goodreads_reviews['work_ratings_count'],
        "average_score": goodreads_reviews['average_rating']
    })
    #
