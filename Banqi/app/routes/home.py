from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user
from .. import db

home_bp = Blueprint('home', __name__, url_prefix='/home')
@home_bp.route('/', methods = ['POST', 'GET'])
def home():
    return render_template('home.html')