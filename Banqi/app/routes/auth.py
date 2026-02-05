from flask import Blueprint, flash, render_template, url_for, redirect, current_app
from flask_bcrypt import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from .models import User, Player, Game
from .forms import LoginForm, RegisterForm
from .. import db, bcrypt
from flask import session
from sqlalchemy import func

# Create a blueprint - make sure all BPs have unique names
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])

# login function
def login():
    loginform = LoginForm() # create login form instance
    error = None 
    if loginform.validate_on_submit():
        username = loginform.username.data # get email from the login form
        password = loginform.password.data # get password from the login form
        user = db.session.scalar(db.select(User).where(User.username==username)) # query the database for the user with the provided email
        if user is None: 
            error = 'This email is not registered. Please register first.' 
        elif not check_password_hash(user.password_hash, password): #check if the provided password matches the stored hashed password
            error = 'Incorrect password'
        if error is None:
            login_user(user)
            flash('Logged in successfully.')
            return redirect(url_for('home.home')) # redirect to the main index page upon successful login
        else:
            flash(error)
    return render_template('user.html', form=loginform,  heading='Login')




@auth_bp.route('/register', methods = ['GET', 'POST'])
def register():
    registerform = RegisterForm() # create register form instance
    if registerform.validate_on_submit():
        username = registerform.username.data
        password = registerform.password.data
        
        # create a hashed password
        # use bcrypt instance to generate hash and store as utf-8 string
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        #if user already exists, warning is flashed to user
        existing_user = db.session.scalar(db.select(User).where(User.username==username))
        if existing_user:
            flash('A user with that email already exists. Please log in.')
            return redirect(url_for('auth.login'))
        
        #create a new user model object
        new_user = User()
        new_user.username = username
        new_user.password_hash = password_hash
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash('Logged in successfully.')
        return redirect(url_for('home.home'))
    
    # if there are validation errors, flash them to the user
    else:
        if registerform.errors:
            for err_msg in registerform.errors.values():
                flash(f'Error registering user: {err_msg}')

    return render_template('user.html', form=registerform, heading='Register')


# Logout route
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('home.home'))


# Profile route
@auth_bp.route('/profile/<username>')
def profile(username):
    user = db.session.scalar(db.select(User).where(User.username==username))
    
    if user is None:
        flash(f'User "{username}" not found.')
        return redirect(url_for('home.home'))
    
    # Calculate stats
    # Get all games for this user
    player_records = Player.query.filter_by(user_id=user.id).all()
    
    # Total games played
    total_games = len(player_records)
    
    # Count wins
    wins = sum(1 for p in player_records if p.result == 'win')
    
    # Calculate win rate
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    
    # Get leaderboard rank based on ELO
    # Count how many users have higher ELO
    users_with_higher_elo = db.session.query(User).filter(User.elo > user.elo).count()
    leaderboard_rank = users_with_higher_elo + 1
    
    stats = {
        'total_games': total_games,
        'wins': wins,
        'win_rate': round(win_rate, 2),
        'elo': round(user.elo, 0),
        'leaderboard_rank': leaderboard_rank
    }
    
    return render_template('bootstrap5/profile.html', stats=stats, user=user)

