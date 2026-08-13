import os

import mysql.connector
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Polling App",
    page_icon="static/images/favicon logo light.webp",
    layout="wide",
)


SAMPLE_LGAS = [
    {"lga_id": 1, "lga_name": "Aniocha North"},
    {"lga_id": 2, "lga_name": "Oshimili South"},
    {"lga_id": 3, "lga_name": "Warri South"},
]

SAMPLE_POLLING_UNITS = [
    {"uniqueid": 1, "polling_unit_name": "Central Primary School", "lga_id": 1},
    {"uniqueid": 2, "polling_unit_name": "Town Hall Ward 2", "lga_id": 1},
    {"uniqueid": 3, "polling_unit_name": "Ogwashi Community Hall", "lga_id": 2},
    {"uniqueid": 4, "polling_unit_name": "Marine Gate Polling Unit", "lga_id": 3},
]

SAMPLE_RESULTS = [
    {"polling_unit_uniqueid": 1, "party_abbreviation": "PDP", "party_score": 124},
    {"polling_unit_uniqueid": 1, "party_abbreviation": "APC", "party_score": 98},
    {"polling_unit_uniqueid": 1, "party_abbreviation": "LP", "party_score": 76},
    {"polling_unit_uniqueid": 2, "party_abbreviation": "PDP", "party_score": 88},
    {"polling_unit_uniqueid": 2, "party_abbreviation": "APC", "party_score": 132},
    {"polling_unit_uniqueid": 2, "party_abbreviation": "LP", "party_score": 45},
    {"polling_unit_uniqueid": 3, "party_abbreviation": "PDP", "party_score": 140},
    {"polling_unit_uniqueid": 3, "party_abbreviation": "APC", "party_score": 67},
    {"polling_unit_uniqueid": 3, "party_abbreviation": "LP", "party_score": 110},
    {"polling_unit_uniqueid": 4, "party_abbreviation": "PDP", "party_score": 72},
    {"polling_unit_uniqueid": 4, "party_abbreviation": "APC", "party_score": 156},
    {"polling_unit_uniqueid": 4, "party_abbreviation": "LP", "party_score": 92},
]


def init_demo_data():
    if "demo_lgas" not in st.session_state:
        st.session_state.demo_lgas = [row.copy() for row in SAMPLE_LGAS]
    if "demo_polling_units" not in st.session_state:
        st.session_state.demo_polling_units = [
            row.copy() for row in SAMPLE_POLLING_UNITS
        ]
    if "demo_results" not in st.session_state:
        st.session_state.demo_results = [row.copy() for row in SAMPLE_RESULTS]


def get_secret_section(name):
    try:
        return st.secrets.get(name, {})
    except Exception:
        return {}


def get_config_value(key):
    env_key = f"MYSQL_{key.upper()}"
    if os.getenv(env_key):
        return os.getenv(env_key)

    mysql_secrets = get_secret_section("mysql")
    if mysql_secrets.get(key):
        return mysql_secrets[key]

    return None


def has_mysql_config():
    return all(
        get_config_value(key)
        for key in ["host", "user", "password", "port", "database"]
    )


def use_demo_data():
    return st.session_state.get("data_source") == "Demo data"


def get_db_connection():
    missing_keys = [
        key
        for key in ["host", "user", "password", "port", "database"]
        if not get_config_value(key)
    ]
    if missing_keys:
        st.error(f"Missing MySQL setting(s): {', '.join(missing_keys)}")
        st.stop()

    return mysql.connector.connect(
        host=get_config_value("host"),
        user=get_config_value("user"),
        password=get_config_value("password"),
        port=get_config_value("port"),
        database=get_config_value("database"),
    )


def fetch_all(query, params=None):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def execute_write(query, params):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def get_lgas():
    if use_demo_data():
        return sorted(st.session_state.demo_lgas, key=lambda row: row["lga_name"])

    return fetch_all("SELECT lga_id, lga_name FROM lga ORDER BY lga_name")


def get_polling_units():
    if use_demo_data():
        return sorted(
            [
                {
                    "uniqueid": row["uniqueid"],
                    "polling_unit_name": row["polling_unit_name"],
                }
                for row in st.session_state.demo_polling_units
            ],
            key=lambda row: row["polling_unit_name"],
        )

    return fetch_all(
        "SELECT uniqueid, polling_unit_name FROM polling_unit ORDER BY polling_unit_name"
    )


def get_parties():
    if use_demo_data():
        parties = {
            row["party_abbreviation"] for row in st.session_state.demo_results
        }
        return [{"party_abbreviation": party} for party in sorted(parties)]

    return fetch_all(
        "SELECT DISTINCT party_abbreviation FROM announced_pu_results "
        "ORDER BY party_abbreviation"
    )


def get_polling_unit_results(polling_unit_id):
    if use_demo_data():
        return sorted(
            [
                {
                    "party_abbreviation": row["party_abbreviation"],
                    "party_score": row["party_score"],
                }
                for row in st.session_state.demo_results
                if row["polling_unit_uniqueid"] == polling_unit_id
            ],
            key=lambda row: row["party_abbreviation"],
        )

    return fetch_all(
        """
        SELECT party_abbreviation, party_score
        FROM announced_pu_results
        WHERE polling_unit_uniqueid = %s
        ORDER BY party_abbreviation
        """,
        (polling_unit_id,),
    )


def get_lga_results(lga_id):
    if use_demo_data():
        polling_unit_ids = {
            row["uniqueid"]
            for row in st.session_state.demo_polling_units
            if row["lga_id"] == lga_id
        }
        totals = {}
        for row in st.session_state.demo_results:
            if row["polling_unit_uniqueid"] in polling_unit_ids:
                party = row["party_abbreviation"]
                totals[party] = totals.get(party, 0) + row["party_score"]

        return [
            {"party_abbreviation": party, "total_score": score}
            for party, score in sorted(totals.items())
        ]

    return fetch_all(
        """
        SELECT party_abbreviation, SUM(party_score) AS total_score
        FROM announced_pu_results
        WHERE polling_unit_uniqueid IN (
            SELECT uniqueid FROM polling_unit WHERE lga_id = %s
        )
        GROUP BY party_abbreviation
        ORDER BY party_abbreviation
        """,
        (lga_id,),
    )


def result_exists(polling_unit_id, party):
    if use_demo_data():
        return any(
            row["polling_unit_uniqueid"] == polling_unit_id
            and row["party_abbreviation"] == party
            for row in st.session_state.demo_results
        )

    rows = fetch_all(
        """
        SELECT 1
        FROM announced_pu_results
        WHERE polling_unit_uniqueid = %s AND party_abbreviation = %s
        LIMIT 1
        """,
        (polling_unit_id, party),
    )
    return bool(rows)


def upsert_result(polling_unit_id, party, score):
    if use_demo_data():
        for row in st.session_state.demo_results:
            if (
                row["polling_unit_uniqueid"] == polling_unit_id
                and row["party_abbreviation"] == party
            ):
                row["party_score"] = score
                return

        st.session_state.demo_results.append(
            {
                "polling_unit_uniqueid": polling_unit_id,
                "party_abbreviation": party,
                "party_score": score,
            }
        )
        return

    if result_exists(polling_unit_id, party):
        execute_write(
            """
            UPDATE announced_pu_results
            SET party_score = %s
            WHERE polling_unit_uniqueid = %s AND party_abbreviation = %s
            """,
            (score, polling_unit_id, party),
        )
    else:
        execute_write(
            """
            INSERT INTO announced_pu_results
                (polling_unit_uniqueid, party_abbreviation, party_score)
            VALUES (%s, %s, %s)
            """,
            (polling_unit_id, party, score),
        )


def show_results_table(rows, score_column):
    if not rows:
        st.info("No results found.")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)
    total = int(df[score_column].fillna(0).sum())
    st.metric("Total votes", f"{total:,}")


def render_home():
    st.title("Polling App")
    st.write("View polling unit results, review LGA totals, and store new results.")

    if use_demo_data():
        st.info(
            "Demo data mode is active. Saved results work in this browser session, "
            "but they are not permanent."
        )

    image_path = "static/images/election.webp"
    if os.path.exists(image_path):
        st.image(image_path, width="stretch")


def render_polling_unit_results():
    st.header("Polling Unit Results")
    polling_unit_id = st.number_input(
        "Polling unit unique ID",
        min_value=1,
        step=1,
        value=1,
    )

    if st.button("Fetch polling unit results", type="primary"):
        try:
            rows = get_polling_unit_results(int(polling_unit_id))
            show_results_table(rows, "party_score")
        except mysql.connector.Error as exc:
            st.error(f"Database error: {exc}")


def render_lga_results():
    st.header("LGA Results")

    try:
        lgas = get_lgas()
    except mysql.connector.Error as exc:
        st.error(f"Database error: {exc}")
        return

    if not lgas:
        st.info("No LGAs available.")
        return

    lga_by_name = {f"{row['lga_name']} ({row['lga_id']})": row["lga_id"] for row in lgas}
    selected_name = st.selectbox("Select LGA", list(lga_by_name.keys()))

    if st.button("Fetch LGA results", type="primary"):
        try:
            rows = get_lga_results(lga_by_name[selected_name])
            show_results_table(rows, "total_score")
        except mysql.connector.Error as exc:
            st.error(f"Database error: {exc}")


def render_add_results():
    st.header("Store New Polling Unit Results")

    try:
        polling_units = get_polling_units()
        parties = get_parties()
    except mysql.connector.Error as exc:
        st.error(f"Database error: {exc}")
        return

    if not polling_units or not parties:
        st.info("Polling units or parties are not available.")
        return

    polling_unit_options = {
        f"{row['polling_unit_name']} ({row['uniqueid']})": row["uniqueid"]
        for row in polling_units
    }
    party_options = [row["party_abbreviation"] for row in parties]

    with st.form("add_result_form"):
        selected_polling_unit = st.selectbox(
            "Polling unit",
            list(polling_unit_options.keys()),
        )
        selected_party = st.selectbox("Party", party_options)
        score = st.number_input("Party score", min_value=0, step=1)
        submitted = st.form_submit_button("Save result", type="primary")

    if submitted:
        polling_unit_id = polling_unit_options[selected_polling_unit]
        try:
            upsert_result(polling_unit_id, selected_party, int(score))
            st.success("Result saved successfully.")
            rows = get_polling_unit_results(polling_unit_id)
            show_results_table(rows, "party_score")
        except mysql.connector.Error as exc:
            st.error(f"Database error: {exc}")


init_demo_data()

data_source_options = ["Demo data", "MySQL database"]
default_data_source = "Demo data"
st.sidebar.selectbox(
    "Data source",
    data_source_options,
    index=data_source_options.index(default_data_source),
    key="data_source",
)

if use_demo_data():
    st.sidebar.caption("Using built-in sample data.")
else:
    st.sidebar.caption("Using MySQL credentials from Streamlit Secrets.")

page = st.sidebar.radio(
    "Navigation",
    [
        "Home",
        "Polling Unit Results",
        "LGA Results",
        "Store New Results",
    ],
)

if page == "Home":
    render_home()
elif page == "Polling Unit Results":
    render_polling_unit_results()
elif page == "LGA Results":
    render_lga_results()
else:
    render_add_results()
