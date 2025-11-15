"""
Django settings for sangabiz project.
"""

from pathlib import Path
import os
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-p-8cakys+ff2=@ug-r__yilt%sli8bn4%3+hh30+c9$j$=^z*%')

# Set DEBUG based on environment variable
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Your VPS IP and domain
VPS_IP = '72.61.200.13'
VPS_DOMAIN = 'sangabiz.com'

ALLOWED_HOSTS = [
    'sangabiz.com',
    'www.sangabiz.com',
    '127.0.0.1',
    'localhost',
    '72.61.200.13',  # your VPS IP
    
]


# CSRF trusted origins for your domain
CSRF_TRUSTED_ORIGINS = [
    f'https://{VPS_DOMAIN}',
    f'https://www.{VPS_DOMAIN}',
    f'https://{VPS_IP}',
    'https://sangabizug.onrender.com',
    'https://sangabizz.onrender.com',
]

INSTALLED_APPS = [

    'unfold',
    'cloudinary',
    'cloudinary_storage',
    'django.contrib.humanize',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'crispy_bootstrap5',
    'storages',

    # Custom apps 
    'accounts',
    'music',
    'artists', 
    'analytics',
    'payments',
    'library',  
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sangabiz.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'music.context_processors.genres',
            ],
        },
    },
]

WSGI_APPLICATION = 'sangabiz.wsgi.application'

# Database Configuration for VPS - PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'sangabiz_db'),
        'USER': os.getenv('DB_USER', 'sangabiz'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'Bens.77532'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Fallback to SQLite if PostgreSQL not configured
if not os.getenv('DB_NAME'):
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [ BASE_DIR / 'static' ]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'



# Cloudinary configuration for media storage (optional)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET', ''),
}

# If Cloudinary credentials are set, use Cloudinary for media storage
if all([os.getenv('CLOUDINARY_CLOUD_NAME'), os.getenv('CLOUDINARY_API_KEY'), os.getenv('CLOUDINARY_API_SECRET')]):
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Email settings
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', f'noreply@{VPS_DOMAIN}')

# File upload settings (increased for music files)
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB

# Security settings for production
if not DEBUG:
    # Security settings
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
else:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False

# WhiteNoise configuration
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Jazzmin Settings
JAZZMIN_SETTINGS = {
    # Title on the brand (19 chars max)
    "site_brand": "Sangabiz Admin",
    
    # Title on the login screen
    "site_header": "Sangabiz",
    
    # Welcome text on the login screen
    "welcome_sign": f"Welcome to {VPS_DOMAIN} Admin",
    
    # Copyright on the footer
    "copyright": f"2024 {VPS_DOMAIN}",
    
    # The model admin to search from the search bar
    "search_model": "auth.User",
    
    # Field name on user model that contains avatar image
    "user_avatar": None,
    
    ############
    # Top Menu #
    ############
    
    # Links to put along the top menu
    "topmenu_links": [
        # Url that gets reversed (Permissions can be added)
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]},
        
        # external url that opens in a new window (Permissions can be added)
        {"name": "View Site", "url": "/", "new_window": True},
        
        # model admin to link to (Permissions checked against model)
        {"model": "auth.User"},
        
        # App with dropdown menu to all its models pages (Permissions checked against models)
        {"app": "music"},
        {"app": "artists"},
        {"app": "accounts"},
        {"app": "analytics"},
        {"app": "payments"},
        {"app": "library"},
    ],
    
    #############
    # User Menu #
    #############
    
    # Additional links to include in the user menu on the top right
    "usermenu_links": [
        {"name": "Support", "url": f"https://{VPS_DOMAIN}/support", "new_window": True},
        {"model": "auth.user"}
    ],
    
    #############
    # Side Menu #
    #############
    
    # Whether to display the side menu
    "show_sidebar": True,
    
    # Whether to aut expand the menu
    "navigation_expanded": True,
    
    # Hide these apps when generating side menu
    "hide_apps": [],
    
    # Hide these models when generating side menu
    "hide_models": [],
    
    # List of apps to base side menu ordering off of
    "order_with_respect_to": ["auth", "music", "artists", "accounts", "analytics", "payments", "library"],
    
    # Custom links to append to app groups, keyed on app name
    "custom_links": {
        "music": [{
            "name": "Upload Songs", 
            "url": "admin:music_song_add", 
            "icon": "fas fa-upload",
            "permissions": ["music.add_song"]
        }],
        "analytics": [{
            "name": "View Reports", 
            "url": "admin:analytics_songplay_changelist", 
            "icon": "fas fa-chart-bar",
            "permissions": ["analytics.view_songplay"]
        }]
    },
    
    # Custom icons for side menu apps/models
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "music.Song": "fas fa-music",
        "music.Genre": "fas fa-tags",
        "music.Album": "fas fa-compact-disc",
        "music.YouTubeVideo": "fas fa-video",
        "artists.Artist": "fas fa-microphone-alt",
        "accounts.UserProfile": "fas fa-user-circle",
        "analytics.SongPlay": "fas fa-chart-line",
        "analytics.UserActivity": "fas fa-user-check",
        "payments.Subscription": "fas fa-credit-card",
        "payments.Transaction": "fas fa-receipt",
        "library.Playlist": "fas fa-list",
        "library.Favorite": "fas fa-heart",
    },
    
    # Icons that are used when one is not manually specified
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    
    #################
    # Related Modal #
    #################
    
    # Use modals instead of popups
    "related_modal_active": True,
    
    #############
    # UI Tweaks #
    #############
    
    # Relative paths to custom CSS/JS scripts
    "custom_css": None,
    "custom_js": None,
    
    # Whether to show the UI customizer on the sidebar
    "show_ui_builder": True,
    
    ###############
    # Change view #
    ###############
    
    # Render out the change view as a single form, or in tabs, current options are:
    # - single
    # - horizontal_tabs (default)
    # - vertical_tabs
    # - collapsible
    # - carousel
    "changeform_format": "horizontal_tabs",
    
    # override change forms on a per modeladmin basis
    "changeform_format_overrides": {
        "auth.user": "collapsible", 
        "auth.group": "vertical_tabs",
        "music.Song": "collapsible",
    },
    
    # Add a language dropdown into the admin
    "language_chooser": False,
}

# Jazzmin UI Tweaks
JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-primary",
    "accent": "accent-primary",
    "navbar": "navbar-white navbar-light",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-outline-primary",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    },
    "actions_sticky_top": True
}

# Audio file settings
ALLOWED_AUDIO_EXTENSIONS = ['mp3', 'wav', 'ogg', 'm4a', 'flac']
MAX_AUDIO_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Cache configuration for VPS
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    }
}

# Logging configuration for production
if not DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                'style': '{',
            },
        },
        'handlers': {
            'file': {
                'level': 'ERROR',
                'class': 'logging.FileHandler',
                'filename': os.path.join(BASE_DIR, 'django_errors.log'),
                'formatter': 'verbose',
            },
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['file', 'console'],
                'level': 'ERROR',
                'propagate': True,
            },
            'music': {
                'handlers': ['file', 'console'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }

# Custom settings
SITE_NAME = "Sangabiz"
SITE_DOMAIN = VPS_DOMAIN
