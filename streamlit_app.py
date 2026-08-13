import os

import mysql.connector
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Polling App",
    page_icon="static/images/favicon logo light.webp",
    layout="wide",
)


def get_config_value(key):
    env_key = f"MYSQL_{key.upper()}"
    if os.getenv(env_key):
        return os.getenv(env_key)

    mysql_secrets = st.secrets.get("mysql", {})
    if mysql_secrets.get(key):
        return mysql_secrets[key]

    st.error(f"Missing MySQL setting: {key}")
    st.stop()


def get_db_connection():
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


@st.cache_data(ttl=300)
def get_lgas():
    return fetch_all("SELECT lga_id, lga_name FROM lga ORDER BY lga_name")


@st.cache_data(ttl=300)
def get_polling_units():
    return fetch_all(
        "SELECT uniqueid, polling_unit_name FROM polling_unit ORDER BY polling_unit_name"
    )


@st.cache_data(ttl=300)
def get_parties():
    return fetch_all(
        "SELECT DISTINCT party_abbreviation FROM announced_pu_results "
        "ORDER BY party_abbreviation"
    )


def get_polling_unit_results(polling_unit_id):
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
    st.dataframe(df, use_container_width=True, hide_index=True)
    total = int(df[score_column].fillna(0).sum())
    st.metric("Total votes", f"{total:,}")


def render_home():
    st.title("Polling App")
    st.write("View polling unit results, review LGA totals, and store new results.")

    image_path = "static/images/election.webp"
    if os.path.exists(image_path):
        st.image(image_path, use_container_width=True)


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
            st.cache_data.clear()
            st.success("Result saved successfully.")
            rows = get_polling_unit_results(polling_unit_id)
            show_results_table(rows, "party_score")
        except mysql.connector.Error as exc:
            st.error(f"Database error: {exc}")


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
