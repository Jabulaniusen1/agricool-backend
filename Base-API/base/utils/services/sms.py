from base.settings import DEBUG, ENVIRONMENT, SERVICE_SID, TWILIO_AUTH, TWILIO_SID

# SMS History constants
DEFAULT_MAX_SIZE = 10

# Environment constants  
DEVELOPMENT_ENV = "development"
E2E_ENV = "e2e"

# Twilio status constants
TWILIO_STATUS_ACCEPTED = "accepted"


# -----------------------------------------------------------------------------
# SMSHistory Class
# -----------------------------------------------------------------------------
class SMSHistory:
    """
    A simple in-memory history of SMS messages keyed by phone number.
    
    This class is used in development or E2E (end-to-end) environments to store
    a limited history (default maximum of 10 messages per phone number) of SMS
    messages that would otherwise be sent out.
    """
    def __init__(self, max_size=DEFAULT_MAX_SIZE):
        super().__init__()
        
        # Initialize an empty dictionary to store messages and set the maximum number.
        self.data = {}
        self.max_size = max_size

    def add_item(self, key, item):
        """
        Adds an item to the message history for the given key (phone number).
        Ensures that no more than `max_size` messages are stored per key.
        """
        if key not in self.data:
            self.data[key] = []  # Create a new list for this key if it doesn't exist.
        self.data[key].append(item)  # Append the new message.
        # If the list exceeds max_size, remove the oldest message.
        if len(self.data[key]) > self.max_size:
            self.data[key].pop(0)

    def get_most_recent(self, key):
        """
        Returns the most recent message for the given key (phone number).
        If the key doesn't exist or no messages are stored, returns None.
        """
        if key in self.data and self.data[key]:
            return self.data[key][-1]
        return None


# -----------------------------------------------------------------------------
# Singleton instances for development environments
# -----------------------------------------------------------------------------
# Use the in-memory SMSHistory only in development or E2E environments.
history = SMSHistory(max_size=DEFAULT_MAX_SIZE) if ENVIRONMENT in (DEVELOPMENT_ENV, E2E_ENV) else None
client = None

# Initialize the Twilio Client if the required credentials are provided.
if TWILIO_SID and TWILIO_AUTH:
    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_AUTH)
    except ImportError as e:
        print(f"Failed to import Twilio client: {e}")
        client = None
    except Exception as e:
        print(f"Failed to initialize Twilio client: {e}")
        client = None


# -----------------------------------------------------------------------------
# SMS Functions
# -----------------------------------------------------------------------------
def send_sms(phone_number, message):
    """
    Sends an SMS message to the specified phone number.
    
    In development/E2E environments, the message is not actually sent but recorded in the history.
    For production, it uses the Twilio client to send the message.
    
    Raises:
        Exception: If the message fails to be accepted by Twilio.
    """
    # Record the SMS in history if we're in a development/E2E environment.
    if history:
        history.add_item(phone_number, message)

    # In development/E2E or if the Twilio client is not available, print and skip sending.
    if ENVIRONMENT in (DEVELOPMENT_ENV, E2E_ENV) or DEBUG or not client:
        print(f"Skipping sending message to {phone_number}.")
        print(f"Message content:\n{message}")
        return

    # Send the SMS using Twilio's API.
    try:
        sent_message = client.messages.create(
            messaging_service_sid=SERVICE_SID,
            body=message,
            to=str(phone_number)
        )

        # Check the message status; if not accepted, raise an exception.
        if sent_message.status != TWILIO_STATUS_ACCEPTED:
            raise Exception(f"Twilio message failed with status: {sent_message.error_message}")
    except Exception as e:
        raise Exception(f"Failed to send SMS to {phone_number}: {str(e)}")


def get_last_sms_sent(phone_number):
    """
    Retrieves the most recent SMS message sent to the specified phone number.
    
    Returns:
        The most recent message if available (development/E2E only), or None.
    """
    if history:
        return history.get_most_recent(phone_number)
    return None
