import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MinMaxScaler
from flask import Flask, request, render_template, redirect, session, url_for, flash
from flask_login import login_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
import hashlib


app = Flask(__name__)
app.secret_key = 'secret_key'


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))

    def __init__(self, username, password):
        self.username = username
        self.password = password


df = pd.read_csv('SpotifySongs.csv')
df = df.drop_duplicates()
song_names = df['SongName']
df = df.drop(['SongName', 'ArtistName'], axis=1)
scaler = MinMaxScaler()
df_scaled = scaler.fit_transform(df)
df = pd.DataFrame(df_scaled, columns=df.columns)
model = NearestNeighbors(n_neighbors=5, algorithm='ball_tree')
model.fit(df)

with app.app_context():
    inspector = inspect(db.engine)
    if not inspector.has_table("user"):
        db.create_all()


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user = User.query.filter_by(username=username, password=hashed_password).first()
        if user:
            session['user_id'] = user.id
            session.pop('error_message', None)
            return redirect('/')
        else:
            error_message = 'Invalid username or password'
            session['error_message'] = error_message
            return render_template('login.html', error_message=error_message)

    error_message = session.pop('error_message', None)
    return render_template('login.html', error_message=error_message)


@app.route('/', methods=['GET', 'POST'])
def home():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    # if request.method == 'POST':
    #     song = request.form['song']
    #     if song not in song_names.values:
    #         return render_template('error.html', message='Song not found')
    #
    #     song_index = song_names[song_names == song].index[0]
    #     query = df[df.index == song_index]
    #     distances, indices = model.kneighbors(query, n_neighbors=5)
    #     recommendations = song_names.iloc[indices[0]].tolist()
    #
    #     return render_template('recommend.html', recommendations=recommendations)

    if request.method == 'POST':
        song = request.form['song'].lower()  # convert user input to lower case
        song_matches = song_names.str.lower().str.contains(song)
        if not song_matches.any():
            return render_template('error.html', message='Song not found')

        song_index = song_matches.idxmax()
        query = df.loc[[song_index]]
        distances, indices = model.kneighbors(query, n_neighbors=5)
        recommendations = song_names.iloc[indices[0]].tolist()

        return render_template('recommend.html', recommendations=recommendations)

    return render_template('home.html')


if __name__ == '__main__':
    app.run(debug=True)
