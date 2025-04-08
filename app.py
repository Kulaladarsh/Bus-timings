from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['bus_timings']
timings_collection = db['timings']

PASS_CODE = "8861"

# Helper function to verify admin passcode
def verify_passcode(passcode):
    return passcode == PASS_CODE

# Home route
@app.route('/')
def index():
    return render_template('index.html')

# Upload form
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'entry_id' not in request.form and not verify_passcode(request.form.get('passcode', '')):
            flash('❌ Invalid admin passcode!', 'error')
            return redirect(url_for('upload'))

        existing_timing = timings_collection.find_one({
            'bus_name': request.form['bus_name'],
            'stop_name': request.form['stop_name'],
            'arrival_time': request.form['arrival_time'],
            'direction': request.form['direction']
        })

        if existing_timing:
            flash('⚠️ This timing already exists!', 'error')
            return redirect(url_for('upload'))

        timing = {
            'bus_no': request.form.get('bus_no', ''),
            'bus_name': request.form['bus_name'],
            'stop_name': request.form['stop_name'],
            'arrival_time': request.form['arrival_time'],
            'decepture_time': request.form['decepture_time'],
            'direction': request.form['direction'],
            'submitted_by': request.form.get('submitted_by', 'Anonymous'),
            'created_at': datetime.now()
        }
        timings_collection.insert_one(timing)
        flash('✅ Timing added successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('upload.html')

# ✅ Search route - corrected to filter by selected direction and stop
@app.route('/search')
def search():
    destination = request.args.get('destination')  # e.g., "Ajekar to Udupi"
    stop_name = request.args.get('stop')           # e.g., "Perdoor"

    buses = []

    if destination and stop_name:
        # Match both direction and stop_name with case-insensitive regex
        query = {
            "direction": {"$regex": f"^{destination}$", "$options": "i"},
            "stop_name": {"$regex": stop_name, "$options": "i"}
        }
        try:
            buses = list(timings_collection.find(query).sort("arrival_time", 1))
        except Exception as e:
            flash(f"❌ Error fetching data: {e}", 'error')
            buses = []
    else:
        buses = []

    return render_template('index.html', buses=buses, selected_direction=destination, selected_stop=stop_name)

# View all timings for a direction
@app.route('/view/<direction>')
def view_direction(direction):
    stops = list(timings_collection.find({'direction': direction}).sort('arrival_time', 1))
    return render_template('view.html', direction=direction, stops=stops)

# Edit existing entry
@app.route('/edit/<entry_id>', methods=['GET', 'POST'])
def edit_entry(entry_id):
    timing = timings_collection.find_one({'_id': ObjectId(entry_id)})
    if not timing:
        flash('❌ Timing not found!', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        if not verify_passcode(request.form.get('passcode', '')):
            flash('❌ Invalid admin passcode!', 'error')
            return redirect(url_for('edit_entry', entry_id=entry_id))

        existing_timing = timings_collection.find_one({
            '_id': {'$ne': ObjectId(entry_id)},
            'bus_name': request.form['bus_name'],
            'stop_name': request.form['stop_name'],
            'arrival_time': request.form['arrival_time'],
            'direction': request.form['direction']
        })

        if existing_timing:
            flash('⚠️ This timing already exists!', 'error')
            return redirect(url_for('edit_entry', entry_id=entry_id))

        timings_collection.update_one(
            {'_id': ObjectId(entry_id)},
            {'$set': {
                'bus_no': request.form.get('bus_no', ''),
                'bus_name': request.form['bus_name'],
                'stop_name': request.form['stop_name'],
                'arrival_time': request.form['arrival_time'],
                'decepture_time': request.form['decepture_time'],
                'direction': request.form['direction'],
                'submitted_by': request.form.get('submitted_by', 'Anonymous'),
                'updated_at': datetime.now()
            }}
        )
        flash('✅ Timing updated successfully!', 'success')
        return redirect(url_for('view_direction', direction=timing['direction']))

    return render_template('upload.html', timing=timing)

# Delete a timing
@app.route('/delete/<entry_id>', methods=["GET", "POST"])
def delete_timing(entry_id):
    timing = timings_collection.find_one({'_id': ObjectId(entry_id)})
    if not timing:
        flash('❌ Timing not found!', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        passcode = request.form.get('passcode', '')
        if not verify_passcode(passcode):
            flash('❌ Invalid admin passcode!', 'danger')
            return redirect(url_for('delete_timing', entry_id=entry_id))

        result = timings_collection.delete_one({'_id': ObjectId(entry_id)})
        if result.deleted_count:
            flash('🗑️ Timing deleted successfully!', 'success')
        else:
            flash('⚠️ Failed to delete timing.', 'danger')

        return redirect(url_for('view_direction', direction=timing['direction']))

    # Render the delete confirmation form
    return render_template('delete.html', timing=timing)


# Run app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
