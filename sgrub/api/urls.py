from django.urls import path
from api.views import AnaliseResiduoView,TreinarModeloView,validalogin,cadastrousuario,salvarrelatorio,enviarpdfporemail,listarrelatoriosusuario,deletarrelatorio,obterrelatorioporid

urlpatterns = [
    path('analise/', AnaliseResiduoView.as_view(), name='analiseresiduo'),
    path('treinar/', TreinarModeloView.as_view(), name='treinarmodelo'),
    path('login/', validalogin.as_view(), name='validalogin'),
    path('cadastro/', cadastrousuario.as_view(), name='cadastrousuario'),
    path('salvarrelatorio/',salvarrelatorio.as_view(), name="salvarrelatorio"),
    path('relatorios/usuario/', listarrelatoriosusuario.as_view(), name='listarrelatoriosusuario'),
    path('relatorio/<int:iderelatorio>/', obterrelatorioporid.as_view(), name='obterrelatorioporid'),
    path('relatorio/<int:iderelatorio>/enviaremail/', enviarpdfporemail.as_view(), name='enviarpdfporemail'),
    path('relatorio/<int:iderelatorio>/excluir/', deletarrelatorio.as_view(), name='deletarrelatorio'),
]
