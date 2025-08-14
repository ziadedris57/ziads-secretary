import streamlit as st
import json
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz

# --- CONFIGURATION ---
# You can change these values to customize the app
CALENDAR_ID = 'primary' # Use 'primary' for the main calendar
TIMEZONE = 'Asia/Riyadh' # Set to your local timezone, e.g., 'America/New_York'
MEETING_DURATION = 30 # in minutes
WORKING_HOURS = {'start': 9, 'end': 17} # 9 AM to 5 PM
WEEKEND_DAYS = [4, 5] # Friday=4, Saturday=5
BUFFER_TIME = 15 # in minutes
SLOTS_TO_SHOW = 5 # How many available slots to show the user

# --- GOOGLE CALENDAR AUTHENTICATION ---
# This function loads the credentials from Streamlit's secrets
def get_calendar_service():
    """Authenticates with Google Calendar API using Service Account."""
    try:
        # st.secrets is a dictionary-like object. We access the nested credentials.
        creds_json = dict(st.secrets["google_credentials"])
        scopes = ['https://www.googleapis.com/auth/calendar']
        creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
        service = build('calendar', 'v3', credentials=creds)
        return service
    except (FileNotFoundError, KeyError) as e:
        st.error("Google credentials not found. Please add them to Streamlit secrets.")
        st.stop()

# --- HELPER FUNCTIONS ---
def find_available_slots(service, start_date, end_date):
    """Finds all available slots between two dates."""
    # Get all busy events from the calendar
    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start_date.isoformat(),
        timeMax=end_date.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    busy_slots = events_result.get('items', [])
    
    available_slots = []
    tz = pytz.timezone(TIMEZONE)
    
    # Start checking from the provided start_date
    current_time = start_date
    
    while current_time < end_date and len(available_slots) < SLOTS_TO_SHOW:
        # Check if current time is within working hours and not a weekend
        if (WORKING_HOURS['start'] <= current_time.hour < WORKING_HOURS['end'] and
            current_time.weekday() not in WEEKEND_DAYS):
            
            slot_end_time = current_time + timedelta(minutes=MEETING_DURATION)
            is_available = True
            
            # Check for conflicts with busy slots
            for event in busy_slots:
                event_start = datetime.fromisoformat(event['start'].get('dateTime').replace('Z', '+00:00')).astimezone(tz)
                event_end = datetime.fromisoformat(event['end'].get('dateTime').replace('Z', '+00:00')).astimezone(tz)
                
                # Check for overlap
                if max(current_time, event_start) < min(slot_end_time, event_end):
                    is_available = False
                    break # Conflict found, no need to check other events
            
            if is_available:
                available_slots.append(current_time)

        # Move to the next potential slot, including buffer time
        current_time += timedelta(minutes=MEETING_DURATION + BUFFER_TIME)
        
    return available_slots

def book_meeting(service, start_time, end_time, summary, description, user_email):
    """Books the meeting on the calendar."""
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': TIMEZONE,
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': TIMEZONE,
        },
        'attendees': [
            {'email': user_email},
        ],
        'reminders': {
            'useDefault': True,
        },
    }
    try:
        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event, sendUpdates='all').execute()
        return created_event
    except Exception as e:
        st.error(f"Failed to book meeting: {e}")
        return None

# --- STREAMLIT APP UI ---

# Initialize session state variables if they don't exist
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False
if 'user_details' not in st.session_state:
    st.session_state.user_details = {}
if 'available_slots' not in st.session_state:
    st.session_state.available_slots = []
if 'slot_selected' not in st.session_state:
    st.session_state.slot_selected = False


# Brenda's personality
st.title("Ziad's Secretary  секретарь Зияда 🤖")
st.markdown("Alright, let's see if he has time for you. Fill this out, and I'll *see* what I can do. No promises. - Brenda")

# --- FORM SUBMISSION LOGIC ---
if not st.session_state.form_submitted:
    with st.form("brenda_form"):
        user_email = st.text_input("Your Email, Honey:", placeholder="So I know where to send the summons")
        topic = st.text_input("What's this about?", placeholder="Keep it brief, I haven't had my second coffee yet.")
        description = st.text_area("Spill the Beans (Description):", placeholder="Lay it all out for me. I'll be the judge of whether it's *actually* important.")
        priority = st.slider("On a scale of 1 to 57, how important do YOU think this is?", min_value=1, max_value=57, value=28)
        
        submitted = st.form_submit_button("Send it to Brenda")

        if submitted:
            if not user_email or not topic:
                st.warning("Honey, I need at least your email and a topic. Let's not waste both our time.")
            else:
                st.session_state.user_details = {
                    "email": user_email,
                    "topic": topic,
                    "description": description,
                    "priority": priority
                }
                st.session_state.form_submitted = True
                # Rerun to move to the next part of the flow
                st.rerun()

# --- SLOT SELECTION LOGIC ---
if st.session_state.form_submitted and not st.session_state.slot_selected:
    st.info("Alright, I've got your info. I'm looking at Ziad's calendar right now... honestly, it's a disaster. But here are a few windows I *might* be able to squeeze you into. Pick one. Quickly.")
    
    # Find and show available slots
    service = get_calendar_service()
    tz = pytz.timezone(TIMEZONE)
    # Start looking for slots from the next hour
    now = datetime.now(tz).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    start_date = now
    end_date = now + timedelta(days=14) # Look 2 weeks ahead
    
    st.session_state.available_slots = find_available_slots(service, start_date, end_date)

    if not st.session_state.available_slots:
        st.error("Yikes. It's even worse than I thought. There are literally no spots available in the next two weeks. Try again later, sweetie.")
    else:
        # Format slots for display
        slot_options = [slot.strftime('%A, %B %d @ %I:%M %p') for slot in st.session_state.available_slots]
        
        selected_slot_str = st.radio(
            "Available Slots:",
            options=slot_options,
            index=0 # Default to the first option
        )
        
        if st.button("Lock It In"):
            # Find the datetime object corresponding to the selected string
            selected_index = slot_options.index(selected_slot_str)
            start_time = st.session_state.available_slots[selected_index]
            end_time = start_time + timedelta(minutes=MEETING_DURATION)
            
            # Book the meeting
            with st.spinner("Brenda is working her magic..."):
                created_event = book_meeting(
                    service,
                    start_time,
                    end_time,
                    summary=st.session_state.user_details['topic'],
                    description=st.session_state.user_details['description'],
                    user_email=st.session_state.user_details['email']
                )

            if created_event:
                st.session_state.slot_selected = True
                st.success("Success! It's on the books. I've sent the official calendar invite to your email. Don't make me regret this.")
                st.balloons()
            else:
                st.error("Oh no, something went wrong and I couldn't book it. You might want to try again.")
