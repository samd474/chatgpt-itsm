from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout 
from django.middleware.csrf import get_token
from rest_framework.decorators import api_view, permission_classes
# Create your views here.
