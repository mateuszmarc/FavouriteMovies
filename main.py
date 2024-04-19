from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy.exc
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, FloatField
from wtforms.validators import DataRequired, Length, NumberRange, URL
import requests
import os
import dotenv


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///favourite-movies.db'
db = SQLAlchemy(app, session_options={"expire_on_commit": False})

Bootstrap(app)
dotenv.load_dotenv('.env')
url = os.getenv('url')
api_key = os.getenv('api_key')
movie_details_base_endpoint = os.getenv('movie_details_base_endpoint')


class MyForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    year = IntegerField('Year', validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired(),
                                                         Length(min=30)])
    rating = FloatField('Rating', validators=[DataRequired(),
                                              NumberRange(min=0.0, max=10.0)])
    ranking = IntegerField('Ranking', validators=[DataRequired(),
                                                  NumberRange(min=1,
                                                              max=10)])
    review = StringField('Review', validators=[DataRequired(),
                                               Length(min=10)])
    img_url = StringField('Img_url', validators=[DataRequired(),
                                                 URL()])
    submit = SubmitField('Add Movie')


class UpdatedMovieForm(FlaskForm):
    new_rating = FloatField('Rating', validators=[DataRequired(),
                                                  NumberRange(min=0.0, max=10.0)])
    new_review = StringField('Review', validators=[DataRequired(),
                                                   Length(min=10)])
    submit = SubmitField('Edit Movie')


class AddMovieFromApiForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    submit = SubmitField('Add Movie')


class Movie(db.Model):
    movie_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    ranking = db.Column(db.String, nullable=False)
    review = db.Column(db.String(500), nullable=False)
    img_url = db.Column(db.String(1000), nullable=False)

    def __repr__(self):
        return self.title


class MovieApiHandler:
    def __init__(self, api_key: str, search_movies_endpoint,
                 movie_details_base_endpoint: str):
        self.api_key = api_key
        self.headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.search_movies_endpoint = search_movies_endpoint
        self.movie_details_base = movie_details_base_endpoint

    def get_movies(self, movie_title: str) -> list:
        params = {
            'query': movie_title
        }

        response = requests.get(self.search_movies_endpoint,
                                headers=self.headers,
                                params=params)
        response.raise_for_status()
        data = [{'id': item['id'],
                 'title': item['original_title'],
                 'year': item['release_date']}
                for item in response.json()['results']]
        return data

    def get_movie(self, movie_id: int) -> dict:
        url = f"{self.movie_details_base}{movie_id}?language=en-US"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        title = data['original_title']
        img_url = f'https://image.tmdb.org/t/p/w500/{data["poster_path"]}'
        year = data['release_date']
        description = data['overview']
        movie_details = {
            'title': title,
            'image_url': img_url,
            'year': year,
            'description': description,
        }
        return movie_details


def check_database():
    with app.app_context():
        try:
            # all_movies = db.session.execute(db.select(Movie).order_by(Movie.rating))
            all_movies = Movie.query.order_by(Movie.rating).all()

        except sqlalchemy.exc.IntegrityError:
            db.create_all()
            all_movies = Movie.query.order_by(Movie.rating).all()
    return all_movies


handler = MovieApiHandler(api_key=api_key,
                          search_movies_endpoint=url,
                          movie_details_base_endpoint=movie_details_base_endpoint)


@app.route("/")
def home():
    all_movies = check_database()
    return render_template("index.html", all_movies=all_movies)


@app.route('/add', methods=['GET', 'POST'])
def add_movie():
    all_movies = check_database()
    form = MyForm()
    if request.method == 'GET':
        return render_template('add.html', form=form)
    else:
        if form.validate_on_submit():
            message = "Movie added successfully!"
            new_movie = Movie()
            new_movie.movie_id = len(all_movies) + 1
            new_movie.title = form.title.data
            new_movie.year = form.year.data
            new_movie.description = form.description.data
            new_movie.rating = float(form.rating.data)
            new_movie.ranking = int(form.ranking.data)
            new_movie.review = form.review.data
            new_movie.img_url = form.img_url.data
            try:
                with app.app_context():
                    db.session.add(new_movie)
                    db.session.commit()
            except sqlalchemy.exc.IntegrityError:
                message = "Something went wrong. Maybe this movie is " \
                          "already on the list?"
            return render_template('add.html', form=form, message=message)
        else:
            message = "Something went wrong. Try again."
            return render_template('add.html', form=form, message=message)


@app.route('/edit', methods=['GET', 'POST'])
def edit_movie():
    form_to_update = UpdatedMovieForm()
    movie_id = request.args.get('id')

    if request.method == 'GET':
        with app.app_context():
            movie_to_update = db.session.get(entity=Movie, ident=movie_id)
        return render_template('edit.html', movie=movie_to_update,
                               form=form_to_update)
    else:
        with app.app_context():
            movie_to_update = db.session.get(entity=Movie, ident=movie_id)
        if form_to_update.validate_on_submit():
            new_rating = form_to_update.new_rating.data
            new_review = form_to_update.new_review.data
            with app.app_context():
                movie_to_update = db.session.get(entity=Movie, ident=movie_id)
                movie_to_update.rating = new_rating
                movie_to_update.review = new_review
                db.session.commit()
            return redirect(url_for('home'))
        else:
            message = "Something Went wrong. Try again."
            return render_template('edit.html',
                                   message=message,
                                   form=form_to_update,
                                   movie=movie_to_update)


@app.route('/delete')
def delete_movie():
    movie_id = request.args.get('id')
    with app.app_context():
        movie_to_delete = db.session.get(entity=Movie, ident=movie_id)
        db.session.delete(movie_to_delete)
        db.session.commit()
    return redirect(url_for('home'))


@app.route('/add_movie_from_api', methods=['GET', 'POST'])
def add_movie_from_api():
    add_form = AddMovieFromApiForm()
    if request.method == 'GET':
        return render_template('add-movie-from-api.html', form=add_form)
    else:
        if add_form.validate_on_submit():
            print('movie validated')
            movie_title = add_form.title.data
            movies = handler.get_movies(movie_title=movie_title)
            return render_template('select.html', movies=movies)
        else:
            return render_template('index.html')


@app.route('/add_blank_movie')
def add_blank_movie():
    all_movies = check_database()
    movie_id = request.args.get('id')
    movie_data = handler.get_movie(int(movie_id))
    blank_movie = Movie()
    blank_movie.movie_id=len(all_movies) + 1
    blank_movie.title=movie_data.get('title')
    blank_movie.year=movie_data.get('year').split('-')[0]
    blank_movie.description=movie_data.get('description')
    blank_movie.rating=movie_data.get('rating', 0)
    blank_movie.ranking=movie_data.get('ranking', "No ranking yet")
    blank_movie.review=movie_data.get('review', "No review yet")
    blank_movie.img_url=movie_data.get('image_url', "No image")

    with app.app_context():
        db.session.add(blank_movie)
        db.session.commit()

    return redirect(url_for('edit_movie', id=blank_movie.movie_id))


if __name__ == '__main__':
    app.run(debug=True)
