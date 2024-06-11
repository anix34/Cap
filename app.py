from flask import Flask, request, redirect, render_template, flash, session, jsonify, g, url_for
import requests
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import connect_db, User, db, Drink, AddDrink
from forms import UserForm, RegisterForm, LoginForm, DrinkForm, UpdateUserForm
import os
import re
from sqlalchemy.exc import IntegrityError

USER_KEY = "curr_user"

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://mixology_user:b4OGduEk6oligRWJ67tbQOsuOJeu23HM@dpg-cpi98lect0pc73fokkk0-a.oregon-postgres.render.com/mixology_5wgz"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.app_context().push()

connect_db(app)
db.create_all()

users = [
    User(id=1, username='user1', password='password1', email='email'),
    User(id=2, username='user2', password='password2', email='email'),
]


# Initialize Flask-Login

login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(username):
    return User.query.filter_by(username = username).first()
    
        
@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for("login"))

#debug = DebugToolbarExtension(app)


# ------------------------------------------------------------- #
# ---------------------- User Routes -------------------------- #
# ------------------------------------------------------------- #

app.config["SECRET_KEY"] = "s3cr1t059"

CURR_USER_KEY = "curr_user"
api_key = 1
BASE_URL = "https://www.thecocktaildb.com/api/json/v1/1/search.php"

def get_name(name):
    res = requests.get(f"{BASE_URL}?s={name}")
    return res.json()['drinks']

def get_drink_id(idDrink):
    if idDrink:
        res = requests.get(f"http://www.thecocktaildb.com/api/json/v1/1/lookup.php?i={idDrink}")
        return res.json()['drinks'][0]
    else:
        return None


def handle_show_drink(user_id, drink_id):
    try:
        added = AddDrink(
        user_id=user_id, drink_id=drink_id)
        db.session.add(added)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        pass

def add_fav(user_id):
    user = User.query.get_or_404(user_id)
    fav = AddDrink.query.filter(
        AddDrink.user_id == user.id).all()
    if len(fav) == 0:
        return None
    else:
        # lst = [drink.id for drink in user.fav]
        lst = []
        for drink in fav:
            res = get_drink_id(drink.drink_id)
            lst.insert(0, res)
        return lst

###############################SEARCH ROUTES################################

@app.route('/')
def homepage():
    return render_template('index.html')

##############################SEARCH BY NAME################################

# @app.route('/search',methods = ['POST'])
# def searched_name():
#     """
#     referenced Cocktail-Dictionary
#     Takes data from form to search for drink lists.

#     """
#     if request.method == 'POST':
#         drink = request.form['search-name']
#         try:
#             res = requests.get(f'{BASE_URL}?s={drink}')
#             val = res.json()
#             all_drinks = val["drinks"]
#             return render_template("cocktail_data.html",all_drinks=all_drinks,drink=drink)
#         except:
#             return " <h1> Oops.. We don't have that cocktail </h1>"
@app.route('/search')
def search():
    term = request.args["search-name"]
    res = get_name(term)
    return render_template('/search.html',term=term,res=res)


###########################SEARCH BY FIRST LETTER##########################
# alph = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','v','w','y','z']

# @app.route('/letters')
# def nav_letters():
#     return render_template('/drinks/nav_letters.html',alph=alph)

# @app.route('/letters/<l>')
# def drink_a(l):
#     res = requests.get(f"{BASE_URL}", params={'api_key': api_key, 'f': {l}})
#     val = res.json()
#     drinks = val["drinks"]
#     return render_template("/drinks/by_letter.html",drinks=drinks, alph=alph)

# @app.route('/searched/<type>',methods=['GET', 'POST'])
# def drink_up(type):
#     drink = type
#     res = requests.get(f'{BASE_URL}?s={drink}')
#     val = res.json()   
#     drinks = val["drinks"]

#     return render_template("/drinks/letter_drink.html", drinks=drinks,drink=drink)

##############################login/register###############################
"""Following Springboard tutorial"""

@app.before_request
def add_user_to_g():
    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])
    else:
        g.user = None

def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id

def do_logout():
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/register', methods=['GET', 'POST'])
def register():
     def is_authenticated():
      if current_user.is_authenticated:
       return redirect(url_for('homepage'))

     form = RegisterForm()

     if request.method == 'POST':
        if form.validate_on_submit():
        # Retrieve form data
          username = request.form['username']
          password = request.form['password']
          email = request.form['email']

        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('signup'))
        if User.query.filter_by(email=email).first():
            flash('Email already exists. Please use a different one.', 'error')
            return redirect(url_for('signup'))

        # Create a new User object
        new_user = User(username=username, password=password, email=email)

        # Set the password for the new user
        new_user.set_password(password)

        # Add the new user to the database
        db.session.add(new_user)
        db.session.commit()

        flash(f'Account created for {username}!', 'success')

        # Redirect to a success page or login page
        return redirect('login')
     else:
        # Render the registration form template for GET requests
        return render_template('/users/register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():

    form = LoginForm()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user:
            if check_password_hash(user.password_hash, password):
                do_login(user)
                flash('Welcome to Mixology!')
                return redirect(url_for('homepage'))
            else:
                flash('Invalid username or password.', 'error')
                return redirect(url_for('login'))
        else:
            flash('Invalid username or password.', 'error')
            return redirect(url_for('login'))

    return render_template('/users/login.html', title='Login', form=form)


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')
    

@app.route('/logout')
def do_logout():
    # Clear the session to log out the user
    session.clear()
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('homepage'))

if __name__ == '__main__':
    app.run(debug=True)


##############################User Route###############################

@app.route('/users/<int:user_id>', methods=["GET", "POST"])
def show_user_page(user_id):
    if not g.user:
        flash("Please login to view your page", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    drinks = Drink.query.filter(Drink.user).all()
    adds = add_fav(user_id)
    form = UpdateUserForm(obj=user)

    if form.validate_on_submit():
        try:
            user.username = form.username.data
            user.email = form.email.data
            db.session.commit()
        except IntegrityError:
            form.username.errors.append('Username or email already in use.  Please pick another')
        flash(f"User {user_id} updated", "success")
        return redirect(f'/users/{user.id}')
    return render_template('/users/show.html',user=user, adds=adds, form=form, drinks=drinks)

@app.route('/users/<int:drink_id>/delete', methods=["POST"])
def remove_drink(drink_id):
    if not g.user:
        flash("Please login first!", "danger")
        return redirect("/")
    
    fav = AddDrink.query.get_or_404(drink_id)
    db.session.delete(fav)
    db.session.commit()
    flash(f"Deleted {fav}")
    return redirect('/')

@app.route('/users/<int:user_id>/fav/')
def show_all_drink(user_id):
    if not g.user:
        flash("Please login first!", "danger")
        return redirect("/")
    user = User.query.get_or_404(user_id)
    org_drink = Drink.query.filter(Drink.user).all()
    adds = add_fav(user_id)
    return render_template("/users/fav.html", org_drink=org_drink,adds=adds,user=user)
##############################loggedIn Route###############################

# @app.route("/user/original/drinks")
# def show_all_org_drink():
#     ""Show list of drink.""
#     if not g.user:
#         flash("Please login first!", "danger")
#         return redirect("/")
#     org_drink = Drink.query.filter(Drink.user).all()
#     return render_template("/drinks/drinks.html", org_drink=org_drink)

@app.route("/user/original/<int:org_id>")
def show_org(org_id):
    org_drink = Drink.query.get_or_404(org_id)
    return render_template("/drinks/drink.html", org_drink=org_drink)

# @app.route("/drinks/<int:drink_id>")
# def show_drink(drink_id):
#     if not g.user:
#         flash("Please login first!", "danger")
#         return redirect("/")
#     handle_show_drink(g.user.id, drink_id)
#     drinks = get_drink_by_id(drink_id)
#     drink = Drink.query.get_or_404(drink_id)
#     return render_template("/drinks/drink.html", drink=drink, drinks=drinks)

@ app.route('/drinks/<int:drink_id>')
def show_drink_page(drink_id):
    if not g.user:
        flash("Please login first!", "danger")
        return redirect("/")
    handle_show_drink(g.user.id, drink_id)
    user = User.query.get_or_404(g.user.id)
    drink = get_drink_id(drink_id)
    return render_template('/drinks/show.html',user=user,drink=drink)
    
@app.route("/drinks/add-drink", methods=["GET", "POST"])
def add_drink():

    form = DrinkForm()
    if not g.user:
        flash("Please login first!", "danger")
        return redirect("/")

    if form.validate_on_submit():
        name = form.name.data
        instructions = form.instructions.data
        ingredient1 = form.ingredient1.data
        ingredient2 = form.ingredient2.data
        ingredient3 = form.ingredient3.data
        ingredient4 = form.ingredient4.data
        ingredient5 = form.ingredient5.data
        ingredient6 = form.ingredient6.data
        ingredient7 = form.ingredient7.data
        ingredient8 = form.ingredient8.data
        ingredient9 = form.ingredient9.data
        ingredient10 = form.ingredient10.data

        drink = Drink(name=name, instructions=instructions, ingredient1 = ingredient1,
        ingredient2 = ingredient2,
        ingredient3 = ingredient3,
        ingredient4 = ingredient4,
        ingredient5 = ingredient5,
        ingredient6 = ingredient6,
        ingredient7 = ingredient7,
        ingredient8 = ingredient8,
        ingredient9 = ingredient9,
        ingredient10 = ingredient10,
        user_id=g.user.id)

        db.session.add(drink)
        db.session.commit()
        flash(f"Added '{name}'")
        return redirect('/')
    else:
        return render_template("/drinks/add_drinks.html", form=form)

@app.route('/drinks/<int:drink_id>/delete', methods=["POST"])
def removee_drink(drink_id):
    if not g.user:
        flash("Please login first!", "danger")
        return redirect("/")
    drink = Drink.query.get_or_404(drink_id)
    
    db.session.delete(drink)
    db.session.commit()
    flash(f"Deleted {drink.name}")
    return redirect("/")


###############################JSON################################

@app.route('/api/drinks')
def list_drinks():
    all_drinks = [drink.serialize() for drink in Drink.query.all()]
    return jsonify(drinks=all_drinks)

@app.route('/api/drinks/<int:id>')
def get_drink(id):
    drink = Drink.query.get_or_404(id)
    return jsonify(drink=drink.serialize())

@app.route('/api/drinks', methods=["POST"])
def create_drink():
    new_drink = Drink(name=request.json["name"])
    db.session.add(new_drink)
    db.session.commit()
    response_json = jsonify(drink=new_drink.serialize())
    return (response_json, 201)

@app.route('/api/drinks/<int:id>', methods=["PATCH"])
def update_drink(id):
    drink = Drink.query.get_or_404(id)
    drink.name = request.json.get('name', drink.name)
    drink.instructions = request.json.get('instructions', drink.instructions)
    drink.ingredient1 = request.json.get('ingredient1', drink.ingredient1)
    drink.ingredient2 = request.json.get('ingredient2', drink.ingredient2)
    drink.ingredient3 = request.json.get('ingredient3', drink.ingredient3)
    drink.ingredient4 = request.json.get('ingredient4', drink.ingredient4)
    drink.ingredient5 = request.json.get('ingredient5', drink.ingredient5)
    drink.ingredient6 = request.json.get('ingredient6', drink.ingredient6)
    drink.ingredient7 = request.json.get('ingredient7', drink.ingredient7)
    drink.ingredient8 = request.json.get('ingredient8', drink.ingredient8)
    drink.ingredient9 = request.json.get('ingredient9', drink.ingredient9)
    drink.ingredient10 = request.json.get('ingredient10', drink.ingredient10)

    db.session.commit()
    return jsonify(drink=drink.serialize())

@app.route('/api/drinks/<int:id>', methods=["DELETE"])
def delete_todo(id):
    
    drink = Drink.query.get_or_404(id)
    db.session.delete(drink)
    db.session.commit()
    return jsonify(message="deleted")
    
if __name__ == '__main__':
    app.run(debug=True) 

