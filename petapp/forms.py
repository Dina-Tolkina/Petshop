from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from petapp.authentication import EmailAuthBackend
from petapp.models import *


class createUserForm(forms.ModelForm):
    last_name = forms.CharField(label='Фамилия', widget=forms.TextInput(attrs={'class': 'form-input'}))
    first_name = forms.CharField(label='Имя', widget=forms.TextInput(attrs={'class': 'form-input'}))
    email = forms.EmailField(label='Электронная почта', widget=forms.EmailInput(attrs={'class': 'form-input'}))
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'class': 'form-input'}))
        
    class Meta:
        model = User
        fields = ('last_name', 'first_name', 'email', 'password')


class RegForm(forms.ModelForm):
    patronymic = forms.CharField(label='Отчество', widget=forms.TextInput(attrs={'class': 'form-input'}))
    phone = forms.CharField(label='Номер телефона', widget=forms.TextInput(attrs={'class': 'form-input', 'id': 'phone'}))
    
    class Meta:
        model = Customer
        fields = ('patronymic', 'phone')


class CombinedRegForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(CombinedRegForm, self).__init__(*args, **kwargs)
        self.fields['last_name'] = createUserForm().fields['last_name']
        self.fields['first_name'] = createUserForm().fields['first_name']
        self.fields['patronymic'] = RegForm().fields['patronymic']
        self.fields['phone'] = RegForm().fields['phone']
        self.fields['email'] = createUserForm().fields['email']
        self.fields['password'] = createUserForm().fields['password']

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if len(last_name) < 2:
            raise forms.ValidationError('Фамилия должна содержать не менее 2 символов.')
        return last_name

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if len(first_name) < 2:
            raise forms.ValidationError('Имя должно содержать не менее 2 символов.')
        return first_name

    def clean_patronymic(self):
        patronymic = self.cleaned_data.get('patronymic')
        if len(patronymic) < 2:
            raise forms.ValidationError('Отчество должно содержать не менее 2 символов.')
        return patronymic
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')

        if Customer.objects.filter(phone=phone).exists():
            self.add_error('phone', 'Пользователь с таким номером телефона уже существует.')

        if User.objects.filter(email=email).exists():
            self.add_error('email', 'Пользователь с такой электронной почтой уже существует.')

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise forms.ValidationError('Пароль должен состоять не менее чем из 8 символов.')
        if not any(char.isupper() for char in password):
            raise forms.ValidationError('Пароль должен содержать хотя бы одну заглавную букву.')
        if not any(char.isdigit() for char in password):
            raise forms.ValidationError('Пароль должен содержать не менее одной цифры.')
        return password


User = get_user_model()

class EmailLoginForm(forms.Form):
    email = forms.EmailField(label='Электронная почта', widget=forms.EmailInput(attrs={'class': 'form-input'}))
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'class': 'form-input'}))


class PaymentForm(forms.Form):
    card_number = forms.CharField(max_length=16, label='Номер карты')
    expiration_date = forms.CharField(max_length=5, label='Срок действия (MM/YY)')
    cvv = forms.CharField(max_length=3, label='CVV')
    shipping_address = forms.CharField(label='Адрес доставки')
