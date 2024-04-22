from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from .models import CustomUser

User = get_user_model()


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254, 
        required=False,  # Make email optional
        help_text='Optional. Inform a valid email address if you wish.', 
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2',)
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class ApiKeyForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['api_key', 'max_chunk_size_setting']
        labels = {
            'api_key': 'OpenAI API Key',
            'max_chunk_size_setting': 'Maximum Chunk Size',
        }
        help_texts = {
            'api_key': 'Enter your personal OpenAI API key. Obtain a key from ' +
                       '<a href="https://platform.openai.com/api-keys" target="_blank">OpenAI API Keys</a>.',
            'max_chunk_size_setting': 'Set the maximum size of text chunks for processing (default is 600 characters).',
        }
        widgets = {
            'api_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your API Key here'}),
            'max_chunk_size_setting': forms.NumberInput(attrs={'class': 'form-control'}),
        }