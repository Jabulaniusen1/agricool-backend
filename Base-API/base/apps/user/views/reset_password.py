from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import translation
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from base.apps.user.models import GenericUserCode, User
from base.celery import app
from base.settings import AUTH_PASSWORD_URL, FRONTEND_URL
from base.utils.recaptcha import validate_recaptcha_field


class ResetPasswordViewSet(GenericViewSet):
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        # Validate reCAPTCHA for all password reset operations
        validate_recaptcha_field(request.data)
        
        if "phoneNumber" in request.data:
            # this is for requesting the reset
            phone_number = request.data["phoneNumber"]
            user = None

            try:
                user = User.objects.get(phone=phone_number)
            except:
                # This endpoint should not disclose whether the user exists or not
                return Response({}, status=200)

            try:
                existing_code = GenericUserCode.objects.get(user=user)
                existing_code.delete()
                existing_code = None
            except:
                existing_code = None

            # to avoid bot spamming, we allow request reset only every 2 hours
            if existing_code:
                if datetime.now().astimezone() < (
                    existing_code.expiration_date.astimezone() - timedelta(hours=4)
                ):
                    return Response(
                        {"error": "Can only request every 2 hours.", "error-code": "2"},
                        status=400,
                    )

            # we replace reset requests for the same number
            if existing_code:
                GenericUserCode.objects.filter(user=user).delete()

            time = datetime.now().astimezone() + timedelta(hours=6)
            code = GenericUserCode.generate_code(phone=phone_number)
            # code = base64.urlsafe_b64encode(os.urandom(6)).decode()
            GenericUserCode.objects.create(
                type="RESET", user=user, code=code, expiration_date=time
            )

            # construct link url
            link = AUTH_PASSWORD_URL.format(
                base_url=FRONTEND_URL,
                code=code,
                phone_number=user.phone,
            )

            if user.email:
                subject = "Password Reset"
                email_from = settings.DEFAULT_FROM_EMAIL
                recipient_list = [user.email]

                try:
                    with translation.override(user.language or "en"):
                        message = translation.gettext("sms_auth_reset_password").format(
                            link=link
                        )
                    send_mail(subject, message, email_from, recipient_list)
                except Exception as e:
                    print(f"[ResetPassword] Failed to send email to {user.email}: {e}")
                    pass

            app.send_task(
                "base.apps.user.tasks.sms.send_sms_auth_reset_password",
                [user.id, phone_number, link],
            )

            return Response({}, status=200)

        else:
            # here we actually reset the password
            phone_number = request.data["phone"]
            password = request.data["password"]
            code = request.data["code"]

            try:
                user = User.objects.get(phone=phone_number)
            except:
                return Response(
                    {"error-message": "User does not exist", "error-code": "1"},
                    status=400,
                )

            try:
                generic_code_object = GenericUserCode.objects.get(code=code)
            except:
                return Response(
                    {"error-message": "Reset not requested", "error-code": "2"},
                    status=400,
                )

            expired = generic_code_object.expiration_date < datetime.now().astimezone()
            if expired:
                return Response(
                    {"error-message": "Reset Code Expired", "error-code": "3"},
                    status=400,
                )

            new_number = generic_code_object.user.phone

            u = User.objects.get(phone=new_number)
            u.set_password(password)
            u.save()

            return Response({"message": "success"}, status=200)
