from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from .models import Casillero
from django.core.exceptions import ValidationError

# Formulario de registro
class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)  # Añadir el campo de email

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']  # Los campos para el registro

# Formulario de login
class UserLoginForm(AuthenticationForm):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput())

class CasilleroPasswordForm(forms.ModelForm):
    class Meta:
        model = Casillero
        fields = ['password']  # Solo incluye el campo de contraseña en el formulario

    def clean_password(self):
        password = self.cleaned_data.get('password')

        # Verifica que la contraseña tenga exactamente 4 dígitos numéricos entre 1 y 6
        if len(password) != 4 or not password.isdigit():
            raise ValidationError('La contraseña debe ser un número de 4 dígitos.')

        # Verifica que los dígitos estén entre 1 y 6
        if any(int(digit) not in range(1, 7) for digit in password):
            raise ValidationError('La contraseña debe estar compuesta solo por números entre 1 y 6.')

        return password
