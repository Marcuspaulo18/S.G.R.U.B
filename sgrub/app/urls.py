from django.urls import path
from app import views

urlpatterns = [
    path('', views.login, name='login'),
    path('index.html', views.index, name='index'),
    path('analise.html', views.analise, name='analise'),
    path('cadastro.html', views.cadastro, name='cadastro'),
    path('historico.html', views.historico, name='historico'),
    path('relatorio.html', views.relatorio, name='relatorio'),
]