import pyotp

class OTP:
    def __init__( self, intervalTime: int = 900 ) -> None:
        """
        initialize function for OTP object
        @param intervalTime: time in second for current OTP expired (default: 900 as 15 minutes)
        """
        self.intervalTime: int = intervalTime
        self.otpSecret = pyotp.random_base32(length=128)

        self.timeOTP: pyotp.TOTP = pyotp.TOTP(self.otpSecret, interval=self.intervalTime, digits=8)

    @property
    def currentOTP(self) -> str:
        """
        return the current otp in otp generated object
        """
        return self.timeOTP.now()

    def verify(self, userProvidedOTP: str) -> bool:
        """
        return value if user provdided otp is verified
        @param userProvidedOTP: user provided otp
        """
        isOTPValid = self.timeOTP.verify(userProvidedOTP)
        return isOTPValid
