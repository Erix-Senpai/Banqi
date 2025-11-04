from flask import Blueprint, redirect, render_template, request, url_for

main_bp = Blueprint('main', __name__, template_folder='../templates')
@main_bp.route('/')
def index():
    return redirect(url_for('home.home'))

