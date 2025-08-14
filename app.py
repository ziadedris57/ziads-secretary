import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz

# --- CONFIGURATION ---
TIMEZONE = 'Asia/Riyadh' # Set your timezone

# --- GOOGLE SHEETS AUTHENTICATION ---
def get_gsheet_client():
    """Authenticates with Google Sheets API."""
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_info(
            st.secrets["google_credentials"], scopes=scopes
        )
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Failed to authenticate with Google Sheets: {e}")
        st.stop()

def save_to_gsheet(client, data):
    """Saves the submitted data to the Google Sheet."""
    try:
        sheet = client.open("Meeting Requests").sheet1
        # Get current timestamp
        now_utc = datetime.now(pytz.utc)
        now_local = now_utc.astimezone(pytz.timezone(TIMEZONE))
        timestamp = now_local.strftime('%Y-%m-%d %H:%M:%S')
        
        # Prepare row data in the correct order
        row = [
            timestamp,
            data['email'],
            data['topic'],
            data['description'],
            data['priority']
        ]
        sheet.append_row(row)
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("Spreadsheet 'Meeting Requests' not found. Please check the name and sharing settings.")
        return False
    except Exception as e:
        st.error(f"Failed to save to Google Sheet probably because Ziad does not want to do this request. He is very tired you know. : {e}")
        return False


# --- STREAMLIT APP UI ---
st.title("Ziad's Secretary 🤖")
st.markdown("Alright, let's see if he has time for you. Fill this out, and I'll place the request on his desk. - Brenda")

st.markdown("---")
st.info("**A Note from Brenda:** Ziad's general availability is Monday - Thursday, 10:00 AM to 4:00 PM Dubai time (GMT+4). Your request will be reviewed for these times.")
st.markdown("---")

# The Form
with st.form("brenda_form", clear_on_submit=True):
    user_email = st.text_input("Your Email, Honey:", placeholder="So we know how to reach you")
    topic = st.text_input("What's this about?", placeholder="Keep it brief, I haven't had my second coffee yet.")
    description = st.text_area("Spill the Beans (Description):", placeholder="Lay it all out for me. I'll be the judge of whether it's *actually* important.")
    priority = st.slider("On a scale of 1 to 57, how important do YOU think this is?", min_value=1, max_value=57, value=28)
    
    submitted = st.form_submit_button("Send it to Brenda's Desk")

if submitted:
    if not user_email or not topic:
        st.warning("Honey, I need at least your email and a topic. Let's not waste both our time.")
    else:
        user_details = {
            "email": user_email,
            "topic": topic,
            "description": description,
            "priority": priority
        }
        with st.spinner("Brenda is filing your request..."):
            client = get_gsheet_client()
            success = save_to_gsheet(client, user_details)
        
        if success:
            st.success("Alright, honey, I've got your request and placed it on Ziad's desk. If a meeting is required, you'll get a separate email from us to coordinate a time. You can close this window now.")
            st.balloons()
