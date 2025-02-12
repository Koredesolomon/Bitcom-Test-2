from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)



# 🔹 Function to Get DB Connection
def get_db_connection():
    return mysql.connector.connect(
        host="ol5tz0yvwp930510.cbetxkdyhwsb.us-east-1.rds.amazonaws.com",
        user="dd5nl96p61stlpkk",  
        password="im8xqo3y6t3m8lni",  
        port="3306",
        database="f3lfgdazfx4amtti"
    )
    
# 🔹 Home Route
@app.route('/')
def index():
    return render_template('index.html')
# 
@app.route('/polling_unit_find')
def polling_unit_find():
    return render_template('polling_unit_find.html')

# 🔹 (Q1) Display results for a specific polling unit
@app.route('/polling_unit/<int:polling_unit_id>')
def polling_unit_results(polling_unit_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT party_abbreviation, party_score 
        FROM announced_pu_results 
        WHERE polling_unit_uniqueid = %s
    """
    cursor.execute(query, (polling_unit_id,))
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('polling_unit.html', polling_unit_id=polling_unit_id, results=results)

# 🔹 (Q1) Display LGA selection
@app.route('/lga_results', methods=['GET'])
def lga_selection():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all LGAs for dropdown
    cursor.execute("SELECT lga_id, lga_name FROM lga")
    lgas = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('lga_results.html', lgas=lgas, results=None)

# 🔹 (Q2) Fetch results for selected LGA
@app.route('/lga_results/<int:lga_id>', methods=['GET'])
def lga_results(lga_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all LGAs for dropdown
    cursor.execute("SELECT lga_id, lga_name FROM lga")
    lgas = cursor.fetchall()

    # Get results for the selected LGA
    query = """
    SELECT party_abbreviation, SUM(party_score) AS total_score 
    FROM announced_pu_results 
    WHERE polling_unit_uniqueid IN (
        SELECT uniqueid FROM polling_unit WHERE lga_id = %s
    )
    GROUP BY party_abbreviation
    """
    cursor.execute(query, (lga_id,))
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('lga_results.html', lgas=lgas, results=results, selected_lga=lga_id)


# 🔹 (Q3) Add new results for a polling unit
@app.route("/add_results", methods=["GET", "POST"])
def add_results():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch available Polling Units
    cursor.execute("SELECT uniqueid, polling_unit_name FROM polling_unit")
    polling_units = cursor.fetchall()

    # Fetch available Parties
    cursor.execute("SELECT DISTINCT party_abbreviation FROM announced_pu_results")
    parties = cursor.fetchall()

    if request.method == "POST":
        polling_unit_uniqueid = request.form["polling_unit_uniqueid"]
        party_abbreviation = request.form["party_abbreviation"]
        party_score = int(request.form["party_score"])

        # Check if a result for the polling unit and party already exists
        cursor.execute("""
            SELECT * FROM announced_pu_results 
            WHERE polling_unit_uniqueid = %s AND party_abbreviation = %s
        """, (polling_unit_uniqueid, party_abbreviation))

        existing_result = cursor.fetchone()

        if existing_result:
            # Update the existing result
            query = """
                UPDATE announced_pu_results
                SET party_score = %s
                WHERE polling_unit_uniqueid = %s AND party_abbreviation = %s
            """
            cursor.execute(query, (party_score, polling_unit_uniqueid, party_abbreviation))
        else:
            # Insert a new result
            query = """
                INSERT INTO announced_pu_results (polling_unit_uniqueid, party_abbreviation, party_score) 
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (polling_unit_uniqueid, party_abbreviation, party_score))

        conn.commit()

        return redirect(url_for("show_results", polling_unit_uniqueid=polling_unit_uniqueid))

    return render_template("add_results.html", polling_units=polling_units, parties=parties)


@app.route("/add_results/<polling_unit_uniqueid>")
def show_results(polling_unit_uniqueid):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch results for the selected polling unit
    cursor.execute("SELECT party_abbreviation, party_score FROM announced_pu_results WHERE polling_unit_uniqueid = %s", (polling_unit_uniqueid,))
    results = cursor.fetchall()

    return render_template("add_results.html", results=results, polling_unit_uniqueid=polling_unit_uniqueid)
# 🔹 Run Flask App
if __name__ == '__main__':
    app.run()