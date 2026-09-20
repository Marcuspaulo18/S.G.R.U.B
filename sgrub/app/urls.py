from django.urls import path

from app import views

urlpatterns = [
    path('', views.index, name='index'),
    path('analise.html', views.analise, name='analise'),
    path('login.html', views.login, name='login'),
    path('cadastro.html', views.cadastro, name='cadastro'),
    path('historico.html', views.historico, name='historico'),
    path('relatorio.html', views.relatorio, name='relatorio'),
]