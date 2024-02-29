import smtplib, ssl

from email.mime.multipart import MIMEMultipart

class Email:
    def __init__( self, SENDER_EMAIL: str, SENDER_PASSWORD: str, SMTP_HOST: str = "smtp.gmail.com", SMTP_PORT: int = 587 ) -> None:
        """
        initialize function for Email object
        @param SENDER_EMAIL: email used for sending
        @param SENDER_PASSWORD: password of sender email
        """
        self.senderEmail: str = SENDER_EMAIL
        self.senderPassword: str = SENDER_PASSWORD

        # setup for host using
        self.smtpHost: str = SMTP_HOST
        self.smtpPort: int = SMTP_PORT

        ## create authentication for sender email

        # use ssl default context for securing with starttls
        self.sslContext: ssl.SSLContext = ssl.create_default_context()

        # create connect
        try:
            self.senderServer: smtplib.SMTP = smtplib.SMTP( self.smtpHost, self.smtpPort )
            self.senderServer.ehlo()
            self.senderServer.starttls( context = self.sslContext ) # setup ssl for starttls
            self.senderServer.ehlo()
            self.senderServer.login( self.senderEmail, self.senderPassword ) # login
        except Exception as e:
            raise e

    def send( self, receiverEmail: str, message: MIMEMultipart ) -> bool:
        """
        send message function for email object
        @param receiverEmail: email to receive the message
        @param message: message for sending
        """
        try:
            self.senderServer.sendmail( self.senderEmail, receiverEmail, message.as_string() )
        except Exception as e:
            raise e
            return False
        else:
            return True
