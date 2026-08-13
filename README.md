# Polling App

This project can run as either the original Flask app or a Streamlit app.

## Run with Flask

```bash
pip install -r requirements.txt
python app.py
```

## Run with Streamlit

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub.
2. Create a new Streamlit app and choose `streamlit_app.py` as the main file.
3. Add these secrets in the Streamlit app settings:

```toml
[mysql]
host = "your-mysql-host"
user = "your-mysql-user"
password = "your-mysql-password"
port = "3306"
database = "your-database-name"
```

The Streamlit app also supports these environment variables:

- `MYSQL_HOST`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_PORT`
- `MYSQL_DATABASE`

If Streamlit shows `Access denied for user ...`, the app reached MySQL but the
database rejected the credentials or the remote host. Check that the Streamlit
secrets exactly match the database credentials, and make sure the database user
is allowed to connect from Streamlit Cloud.
