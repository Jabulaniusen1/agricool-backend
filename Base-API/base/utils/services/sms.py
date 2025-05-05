from base.settings import ENVIRONMENT, SERVICE_SID, TWILIO_AUTH, TWILIO_SID


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
    def __init__(self, max_size=10):
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
history = SMSHistory(max_size=10) if ENVIRONMENT in ("development", "e2e") else None
client = None

# Initialize the Twilio Client if the required credentials are provided.
if TWILIO_SID and TWILIO_AUTH:
    from twilio.rest import Client
    client = Client(TWILIO_SID, TWILIO_AUTH)


# -----------------------------------------------------------------------------
# SMS Functions
# -----------------------------------------------------------------------------
def send_sms(phoneNumber, message):
    """
    Sends an SMS message to the specified phone number.
    
    In development/E2E environments, the message is not actually sent but recorded in the history.
    For production, it uses the Twilio client to send the message.
    
    Raises:
        Exception: If the message fails to be accepted by Twilio.
    """
    # Record the SMS in history if we're in a development/E2E environment.
    if history:
        history.add_item(phoneNumber, message)

    # In development/E2E or if the Twilio client is not available, print and skip sending.
    if ENVIRONMENT in ("development", "e2e") or not client:
        print(f"Skipping sending message to {phoneNumber}.")
        print(f"Message content:\n{message}")
        return

    # Send the SMS using Twilio's API.
    sent_message = client.messages.create(
        messaging_service_sid=SERVICE_SID,
        body=message,
        to=str(phoneNumber)
    )

    # Check the message status; if not accepted, raise an exception.
    if sent_message.status != "accepted":
        raise Exception(f"Twilio message failed with status: {sent_message.error_message}")


def get_last_sms_sent(phoneNumber):
    """
    Retrieves the most recent SMS message sent to the specified phone number.
    
    Returns:
        The most recent message if available (development/E2E only), or None.
    """
    if history:
        return history.get_most_recent(phoneNumber)
    return None
