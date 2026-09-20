from django.shortcuts import render,redirect

def index(request):
    return render(request,'Sgrubapp/index.html')

def analise(request):
    if not request.session.get('ideusuario'):
        return redirect('Sgrubapp/index.html')
    else:
        return render(request,'Sgrubapp/analise.html')

def login(request):
    return render(request,'Sgrubapp/login.html')

def cadastro(request):
    return render(request,'Sgrubapp/cadastro.html')

def historico(request):
    if not request.session.get('ideusuario'):
        return redirect('Sgrubapp/index.html')
    else:
        return render(request,'Sgrubapp/historico.html')

def relatorio(request):
    if not request.session.get('ideusuario'):
        return redirect('Sgrubapp/index.html')
    else:
        return render(request,'Sgrubapp/relatorio.html')

