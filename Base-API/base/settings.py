import os
from datetime import timedelta
from pathlib import Path

import environ
import sentry_sdk

# Gets the project root folder path
BASE_DIR = Path(__file__).resolve().parent
# Gets the name of the environment file passed by the environment variable (In our case passed in docker-compose files)
ENV_FILE = os.getenv("ENV_FILE") or ".env"

# Environ setup
env = environ.Env()

potential_env_file_path = os.path.join(BASE_DIR, ENV_FILE)
if ENV_FILE != "" and os.path.exists(potential_env_file_path):
    environ.Env.read_env(potential_env_file_path)


# Custom function to allow setting a fallback value when fetchin an environ environment value
def getEnv(key, fallback=None):
    try:
        return os.getenv(key) or env(key)
    except:
        if fallback is None:
            raise ValueError(
                f'No environment variable set for key "{key}" and no fallback value provided'
            )
        return fallback


def str_to_bool(s):
    return s.lower() in ["true", "1", "yes"]


##
# Redis
##
REDIS_HOST = getEnv("REDIS_HOST", "localhost")
REDIS_PORT = getEnv("REDIS_PORT", "6379")
REDIS_PASSWORD = getEnv("REDIS_PASSWORD", "")
REDIS_DATABASE = getEnv("REDIS_DATABASE", "0")
REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DATABASE}"

# Celery config
CELERY_ACKS_LATE = True
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

##
# DJANGO
##
ENVIRONMENT = getEnv("ENVIRONMENT", "development")
FRONTEND_URL = getEnv("FRONTEND_URL", "http://localhost:8100")
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 Mb limit
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 Mb limit
SECRET_KEY = getEnv(
    "SECRET_KEY", "changeme"
)  # SECURITY WARNING: keep the secret key used in production secret!
DEBUG = str_to_bool(
    getEnv("DEBUG", "False")
)  # SECURITY WARNING: don't run with debug turned on in production!
LOCALE_PATHS = [
    os.path.join(BASE_DIR, "locale"),
]
URL_BASE_API = os.getenv("URL_BASE_API", "http://localhost:8000")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,  # Update the location based on your Redis setup
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    "corsheaders",
    "django_celery_beat",
    "rest_framework",
    # apps
    "base.apps.user",
    "base.apps.storage",
    "base.apps.operation",
    "base.apps.security",
    "base.apps.prediction",
    "base.apps.marketplace",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

APPEND_SLASH = True

# Import path to the URLconf
# https://docs.djangoproject.com/en/4.1/ref/settings/#root-urlconf
ROOT_URLCONF = "base.urls"

# Templates configuration
# https://docs.djangoproject.com/en/4.1/ref/settings/#templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Path of the wsgi application that Django will use
# https://docs.djangoproject.com/en/4.1/ref/settings/#wsgi-application
WSGI_APPLICATION = "base.wsgi.application"

# Database configuration
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "base.db.backends.postgis",
        # "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": getEnv("DB_NAME", "postgres"),
        "USER": getEnv("DB_USERNAME", "postgres"),
        "PASSWORD": getEnv("DB_PASSWORD", "postgres"),
        "HOST": getEnv("DB_HOST", "localhost"),
        "PORT": getEnv("DB_PORT", "5432"),
    }
}

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Model to represent a user
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-user-model
AUTH_USER_MODEL = "user.User"

# Network configuration
ALLOWED_HOSTS = ["*"]
CORS_ORIGIN_ALLOW_ALL = True
CORS_ORIGIN_WHITELIST = ("http://localhost:8100",)

# Django Rest Framework configuration
# https://www.django-rest-framework.org/
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        #'rest_framework.renderers.BrowsableAPIRenderer',  # Ensure this is included for the Browsable API
    ],
}

# Simple JSON Web Token configuration
# https://django-rest-framework-simplejwt.readthedocs.io/en/latest/
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),  # 1 month
    "REFRESH_TOKEN_LIFETIME": timedelta(days=365),  # 1 year
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}

# Static files (CSS, JavaScript, Images) and medias
# https://docs.djangoproject.com/en/3.2/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "/static/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

# Used to increase the max number of deletable files in admin
DATA_UPLOAD_MAX_NUMBER_FIELDS = int(getEnv("DATA_UPLOAD_MAX_NUMBER_FIELDS", "1000"))

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Settings for users invitation
INVITATION_EXPIRY = timedelta(
    days=int(getEnv("INVITATION_EXPIRY", "1"))
)  # Invitations expire in 1 day by default
INVITATION_CODE_SALT = getEnv("INVITATION_CODE_SALT", "ec*bgxfN4TFfoyFpCmgJ")


# Deep Links

# AUTH_PASSWORD_URL = getEnv("AUTH_PASSWORD_URL", "{base_url}/password-reset/{code}/{phone_number}")
# INVITATION_OPERATOR_URL = getEnv("INVITATION_OPERATOR_URL", "{base_url}/invite/{code}/op/{phone_number}")
# INVITATION_SERVICE_PROVIDER_URL = getEnv("INVITATION_SERVICE_PROVIDER_URL", "{base_url}/invite/{code}/sp/{phone_number}")

AUTH_PASSWORD_URL = getEnv(
    "AUTH_PASSWORD_URL",
    "{base_url}/auth/reset/?resetcode={code}&phoneNumber={phone_number}",
)
INVITATION_OPERATOR_URL = getEnv(
    "INVITATION_OPERATOR_URL",
    "{base_url}/auth/signup-invitation/?user-type=2&invitation-code={code}&phoneNumber={phone_number}",
)
INVITATION_SERVICE_PROVIDER_URL = getEnv(
    "INVITATION_SERVICE_PROVIDER_URL",
    "{base_url}/auth/signup-invitation/?user-type=1&invitation-code={code}&phoneNumber={phone_number}",
)

##
# Internationalization
##
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

##
# Twilio
##
TWILIO_SID = getEnv("TWILIO_SID", "")
SERVICE_SID = getEnv("SERVICE_SID", "")
TWILIO_AUTH = getEnv("TWILIO_AUTH", "")
TWILIO_NUMBER = getEnv("TWILIO_NUMBER", "")

##
# Email
##
DEFAULT_FROM_EMAIL = "no-reply@coldtivate.org"
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "sendgrid_backend.SendgridBackend"
    SENDGRID_API_KEY = os.getenv(
        "SENDGRID_API_KEY"
    )  # Storing API key in environment variable


# Logging for testing
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s [%(name)s:%(lineno)s] %(module)s %(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "gunicorn": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "verbose",
            "filename": "../app_gunicorn_errors.log",
            "maxBytes": 1024 * 1024 * 100,  # 100 mb
        }
    },
    "loggers": {
        "gunicorn.errors": {
            "level": "DEBUG",
            "handlers": ["gunicorn"],
            "propagate": True,
        }
    },
}

# Price prediction
PRICE_PREDICTION_URL_INDIA = (
    os.getenv("PRICE_PREDICTION_URL_INDIA") or "http://scraping_india:5000/prediction"
)
PRICE_PREDICTION_URL_NIGERIA = (
    os.getenv("PRICE_PREDICTION_URL_NIGERIA")
    or "http://scraping_nigeria:5000/prediction"
)

##
# Marketplace
##

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY") or "cH4ng3_m3"
MARKETPLACE_COLDTIVATE_EXPONENT = 0.035  # 3.5%
MARKETPLACE_OPEN_TO_COUNTRIES = ["NG"]

##
# Sentry
##

if ENVIRONMENT != "development":
    sentry_sdk.init(
        dsn="https://c67bfa37f9b1593641a2c37b05b3743d@o4508088181653504.ingest.de.sentry.io/4508088191156304",
        traces_sample_rate=1.0,
        environment=ENVIRONMENT,
    )

##
# Comsol DT Service
##
COMSOL_CALLBACK_KEY = os.getenv("COMSOL_CALLBACK_KEY") or "cH4ng3_m3"
URL_COMSOL_DT_API = (
    os.getenv("COMSOL_DT_API_URL") or "http://comsol_dt_service:5900/api/"
)

##
# reCAPTCHA Configuration
##
# Disable reCAPTCHA for E2E testing environments
if ENVIRONMENT == "e2e":
    RECAPTCHA_ENABLED = False
else:
    RECAPTCHA_ENABLED = str_to_bool(getEnv("RECAPTCHA_ENABLED", "false"))

RECAPTCHA_SECRET_KEY = getEnv("RECAPTCHA_SECRET_KEY", None)
RECAPTCHA_SITE_KEY = getEnv("RECAPTCHA_SITE_KEY", None)