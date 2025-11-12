from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm

class ProfileUpdateForm(UserChangeForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the password field
        self.fields.pop('password')