from flask import Blueprint, render_template, request, url_for, session, flash, redirect, jsonify
from models.database import Admin, Pending, Student, Borrowed, Equipment, db , Completed, Violators
from werkzeug.security import check_password_hash, generate_password_hash
from resource.user import PendingItems, BorrowedItems, CompletedItems, ShowEquipments
import datetime
from route.mail import sendMessage

admin_bp = Blueprint('admin', __name__)

advance_datetime = datetime.datetime.now() + datetime.timedelta(hours=5)

@admin_bp.route('/delete-equipment/<int:id>', methods=['DELETE'])
def delete_equipment(id):
    if 'admin_login' in session and request.method=="DELETE":
        target_equipment = Equipment.query.filter_by(equip_id=id).first()
        if not target_equipment:
            return jsonify({"message": "Item not found"}), 494
        db.session.delete(target_equipment)
        db.session.commit()
        return jsonify({"message": "Equipment deleted"}), 299
    return redirect(url_for('index'))

@admin_bp.route('/edit-equipment/<int:id>', methods=['PUT'])
def edit_equipment(id):
    if 'admin_login' in session and request.method=="PUT":
        target_equipment = Equipment.query.filter_by(equip_id=id).first()
        if not target_equipment:
            return jsonify({"message": "Item not found"}), 494
        data = request.get_json()
        target_equipment.equip_type = data['args_equip_name']
        db.session.commit()
        return jsonify({"message": "Equipment updated"}), 299
    return redirect(url_for('index'))

@admin_bp.route('/save-equipment', methods=['POST'])
def save_equipment():
    if 'admin_login' in session and request.method == "POST":
        equipment_type = request.form['args_equip_type']
        equipment_obj = Equipment(
            equip_type=equipment_type,
            equip_unique_key=ShowEquipments.generate_unique_id(13),
            is_available=1,
            is_pending=0
        )
        db.session.add(equipment_obj)
        db.session.commit()
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('index'))

@admin_bp.route('/option/<option>')
def load_option(option):
    if 'admin_login' in session:
        b_items = BorrowedItems()
        p_items = PendingItems()
        c_items = CompletedItems()
        list_equipments = ShowEquipments()
        violators = Violators.query.order_by(Violators.violator_id.desc()).all()
        Borrowed.penalty_checker()
        
        pending = p_items.get()
        borrowed = b_items.get()
        for i in range(len(borrowed['borrow_id'])):
            if borrowed['time_quota'][i]:
                borrowed['time_quota'][i] = datetime.datetime.strptime(borrowed['time_quota'][i], '%Y-%m-%d %H:%M:%S')
            pass

        completed = c_items.get()
        equipments = list_equipments.get()
        
        content = render_template(f'{option}.html',
                                   borrowed=borrowed, 
                                   pending=pending, 
                                   completed=completed,
                                   equipments=equipments,
                                   violators=violators)
        return content
    return redirect('index')


@admin_bp.route('/return/<int:id>')
def return_item(id):
    if 'admin_login' in session:
        borrowed_obj = Borrowed.query.filter_by(pending_id=id).first()
        pending_obj = Pending.query.filter_by(pending_id=id).first()
        student_obj = Student.query.filter_by(requested_item=pending_obj.equip_unique_key).first()
        equip_obj = Equipment.query.filter_by(equip_unique_key=pending_obj.equip_unique_key).first()
        if borrowed_obj.is_claimed and not borrowed_obj.is_returned:
            borrowed_obj.is_claimed = False
            borrowed_obj.is_returned = True
            student_obj.status = 'returned'
            completed_obj = Completed(
                student_number = student_obj.student_number,
                student_department = student_obj.student_department,
                student_name = f"{student_obj.student_surname}, {student_obj.student_firstname}",
                equip_type = pending_obj.equip_type,
                equip_unique_key = pending_obj.equip_unique_key
            )
            equip_obj.is_available = True
            equip_obj.is_pending = False
            db.session.add(completed_obj)
            db.session.delete(student_obj)
            db.session.delete(pending_obj)
            db.session.delete(borrowed_obj)
            db.session.commit()
            return redirect(url_for('admin.dashboard'))
        return f"It is either the Item isn't Claimed or Returned"
    return redirect(url_for('index'))

@admin_bp.route('/claim/<int:id>')
def claim_item(id):
    if 'admin_login' in session:
        borrowed_obj = Borrowed.query.filter_by(pending_id=id).first()
        pending_obj = Pending.query.filter_by(pending_id=id).first()
        student_obj = Student.query.filter_by(requested_item=pending_obj.equip_unique_key).first()
        if not borrowed_obj.is_claimed and not borrowed_obj.is_returned:
            borrowed_obj.is_claimed = True
            borrowed_obj.time_quota = advance_datetime
            student_obj.status = 'claimed'
            db.session.commit()
            return redirect(url_for('admin.dashboard'))
        return f"It is either the Item isn't Claimed or Returned"
    return redirect(url_for('index'))



@admin_bp.route('/disproof/<int:pending_id>')
def disproof_item(pending_id):
    if 'admin_login' in session:
        pending_obj = Pending.query.filter_by(pending_id=pending_id).first()
        equipment_obj = Equipment.query.filter_by(equip_unique_key=pending_obj.equip_unique_key).first()
        student_obj = Student.query.filter_by(requested_item=pending_obj.equip_unique_key).first()
        borrowed_obj = Borrowed.query.filter_by(pending_id=pending_obj.pending_id).first()
        if not pending_obj.is_verified or not borrowed_obj:
            db.session.delete(pending_obj)
            db.session.delete(student_obj)
            equipment_obj.is_available=1
            equipment_obj.is_pending=0
            db.session.commit()       
            return redirect(url_for('admin.dashboard'))
        return f"""
                <script>
                    alert("Cant delete item");
                    window.location.href='/dashboard';
                </script>
                """
    return redirect(url_for('index'))

@admin_bp.route('/verify/<string:unique>')
def verify_item(unique):
    if 'admin_login' in session:
        pending_obj = Pending.query.filter_by(equip_unique_key=unique).first()
        student_obj = Student.query.filter_by(requested_item=unique).first()
        equipmemt_obj = Equipment.query.filter_by(equip_unique_key=unique).first()
        if not pending_obj.is_verified:
            pending_obj.is_verified=1
            equipmemt_obj.is_available=0
            pending_obj.is_pending=1
            student_obj.status = 'to-receive'
            borrowed_obj = Borrowed(
                time_quota=None,
                is_returned=0,
                pending_id=pending_obj.pending_id
            )
            sendMessage(student_obj, equipmemt_obj.equip_type)
            db.session.add(borrowed_obj)
            db.session.commit()
            return redirect(url_for('admin.dashboard'))
        return f"""
                <script>
                    alert("Item Key: [{ pending_obj.equip_unique_key }] already Verified and Ongoing to StudentID: [{student_obj.student_number}] with Status: [{student_obj.status}]");
                    window.location.href='/dashboard';
                </script>
                """
    return redirect(url_for('index'))

#render the pending items student requested
#dashboard route
@admin_bp.route('/dashboard', methods=['POST', 'GET'])
def dashboard():
    if 'admin_login' in session:
        unverified = Pending.query.filter_by(is_verified=False).count()
        current_user = Admin.query.filter_by(admin_username=session.get('admin_login', "")).first()
        return render_template('dashboard.html', unverified=unverified, current_user=current_user)
    return redirect(url_for('index'))

#check if log in is true
@admin_bp.route('/logged-in', methods=['POST', 'GET'])
def logged_in():
    username, password = request.form.get('input_username').strip(), request.form.get('input_password').strip()
    if Admin.check_login(username, password):
        session['admin_login'] = username
        
        return redirect(url_for('admin.dashboard'))
    
    return "<script>alert('Invalid login credentials'); window.location.href='/';</script>"

@admin_bp.route('/signed-up', methods=["POST", "GET"])
def sign_up():
    admin_email_address, admin_firstname, admin_surname, admin_username, admin_password, admin_password2 = request.form.get('admin_email_address'), request.form.get('admin_firstname'), request.form.get('admin_surname'), request.form.get('admin_username'), request.form.get('admin_password'), request.form.get('admin_password2'),
    if admin_password == admin_password2 and request.method=='POST':
        admin_obj = Admin(
            admin_username=admin_username,
            admin_password=admin_password,
            admin_email_address=admin_email_address,
            admin_firstname=admin_firstname,
            admin_surname=admin_surname
        )
        admin_obj.save()
        return redirect(url_for('index'))
    return "none"

@admin_bp.route('/sign-up-page')
def sign_up_page():
    return render_template('sign-up.html')