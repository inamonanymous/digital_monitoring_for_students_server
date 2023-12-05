from flask import Flask, render_template, request, session
import os
from flask_restful import Api
from resource.user import ShowEquipments, Equipments,  Students, PendingItems, BorrowedItems, CompletedItems, EachStudent
from models.database import db
from flask_cors import CORS
from route.admin import admin_bp

app = Flask(__name__)
CORS(app, resources={r"/user/*": {"origins": ["*"]}}) # asterisk means, it can receive data from any host

app.secret_key = f"your_secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://your_username:your_password@your_database_host/your_database_name"

db.init_app(app)
api = Api(app)

api.add_resource(EachStudent, '/user/student/<string:student_number>')
api.add_resource(Students, '/user/student')
api.add_resource(CompletedItems, '/user/completed-items')
api.add_resource(BorrowedItems, '/user/borrowed-items')
api.add_resource(PendingItems, '/user/pending-items')
api.add_resource(ShowEquipments, '/user/equipments/all')
api.add_resource(Equipments, '/user/equipments/<string:unique_key>')

app.register_blueprint(admin_bp)

@app.route('/', methods=['POST', 'GET'])
def index():
    session.clear()
    return render_template('index.html')


