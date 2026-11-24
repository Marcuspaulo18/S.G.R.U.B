from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from reportlab.lib.pagesizes import letter
import io
from reportlab.pdfgen import canvas
from api.ml import classificarimagem
from api.conectabanco import conn
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import resend
import os
from dotenv import load_dotenv

load_dotenv()
RESENDKEY = os.getenv("RESENDKEY")

class AnaliseResiduoView(APIView):
    def post(self, request):
        arquivo = request.FILES.get('imagem')
        

        if not arquivo:
            return Response(
                {'erro': 'Nenhuma imagem foi enviada. Envie um arquivo via campo "imagem".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        tipos = ['image/jpeg', 'image/png', 'image/jpg']
        if arquivo.content_type not in tipos:
            return Response(
                {'erro': 'Formato nao suportado. Envie arquivos JPG, JPEG ou PNG.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            bytesimagem = arquivo.read()

            resultado = classificarimagem(bytesimagem)

            return Response(resultado, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'erro': f'Erro ao processar a imagem: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TreinarModeloView(APIView):
    def get(self, request):
        try:
            from api.ml import treinarmodelo
            treinarmodelo(epochs=10)
            return Response(
                {'mensagem': 'Modelo treinado e salvo com sucesso.'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'erro': f'Erro ao treinar o modelo: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
@method_decorator(csrf_exempt, name='dispatch')
class validalogin(APIView):
    def post(self,request):
       desemail= request.data.get('email')
       dessenha= request.data.get('senha')

       banco = conn().banco
       cursor = banco.cursor()
       cursor.callproc('spsellogin',[desemail,dessenha])
       row = cursor.fetchone()
       cursor.close()
       banco.close()

       if row:
           usuario={
               'desnomeusuario': row[0] if len(row) > 0 else None,
               'dessenha': row[1] if len(row) > 1 else None,
               'ideusuario': row[2] if len(row) > 2 else None,
               'destelefone': row[3] if len(row) > 3 else None,
               'desprofissao': row[4] if len(row) > 4 else None,
               'nrocpf': row[5] if len(row) > 5 else None,
           }
           request.session['desnomeusuario'] = row[0]
           request.session['ideusuario'] = row[2]
           request.session['desemail'] = desemail
           
           return Response(usuario, status=status.HTTP_200_OK)
       else:
           return Response({'erro': 'Email ou senha incorretos'}, status=status.HTTP_401_UNAUTHORIZED)

@method_decorator(csrf_exempt, name='dispatch')
class cadastrousuario(APIView):
    def post(self, request):
        try:
            tipo_pessoa = request.data.get('tipo_pessoa')  # 'PF' ou 'PJ'

            nome = request.data.get('nome')
            nascimento = request.data.get('nascimento')
            email = request.data.get('email')
            telefone = request.data.get('telefone')
            usuario = request.data.get('usuario')
            senha = request.data.get('senha')

            banco = conn().banco
            cursor = banco.cursor()

            # ----------------------------------------------------
            # 2. Executa a Procedure Base (spinsupusuario)
            # ----------------------------------------------------
            cursor.callproc('spinsupusuario', [
                nome,
                nascimento,
                email,
                telefone,
                usuario,
                senha,
                tipo_pessoa
            ])
            
            # ObtÃ©m o ideusuario gerado/retornado pela procedure
            row = cursor.fetchone()
            if not row:
                cursor.close()
                banco.close()
                return Response({'erro': 'Falha ao registrar usuÃ¡rio base.'}, status=status.HTTP_400_BAD_REQUEST)
            
            ideusuario = row[0]

            # ----------------------------------------------------
            # 3. Executa a Procedure EspecÃ­fica (PF ou PJ)
            # ----------------------------------------------------
            if tipo_pessoa == 'PF':
                cpf = request.data.get('cpf')
                profissao = request.data.get('profissao')
                genero = request.data.get('genero')

                cursor.callproc('spinsupusuariocpf', [
                    ideusuario,
                    cpf,
                    profissao,
                    genero
                ])

            elif tipo_pessoa == 'PJ':
                razao_social = request.data.get('razao_social')
                porte = request.data.get('porte')
                nome_fantasia = request.data.get('nome_fantasia')
                data_fundacao = request.data.get('data_fundacao')
                segmento = request.data.get('segmento')
                link_portal = request.data.get('link_empresa')
                cnpj = request.data.get('cnpj')

                cursor.callproc('spinsupusuariocnpj', [
                    ideusuario,
                    razao_social,
                    porte,
                    nome_fantasia,
                    data_fundacao,
                    segmento,
                    link_portal,
                    cnpj
                ])

            # ----------------------------------------------------
            # 4. Executa a Procedure de EndereÃ§o (spinsupendereco)
            # ----------------------------------------------------
            logradouro = request.data.get('logradouro')
            cep = request.data.get('cep')
            complemento = request.data.get('complemento', '')
            numero = request.data.get('numero')
            bairro = request.data.get('bairro')
            uf = request.data.get('estado')
            cidade = request.data.get('cidade')

            cursor.callproc('spinsupendereco', [
                ideusuario,
                logradouro,
                cep,
                complemento,
                numero,
                bairro,
                uf,
                cidade
            ])

            # FinalizaÃ§Ã£o das transaÃ§Ãµes
            banco.commit()
            cursor.close()
            banco.close()

            # Cria a sessÃ£o
            request.session['desnomeusuario'] = usuario
            request.session['ideusuario'] = ideusuario

            return Response({
                'mensagem': 'Cadastro realizado com sucesso!',
                'ideusuario': ideusuario
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            if 'banco' in locals() and banco:
                banco.rollback()
                cursor.close()
                banco.close()
            return Response({'erro': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Configura a chave da API do Resend
resend.api_key = RESENDKEY

@method_decorator(csrf_exempt, name='dispatch')
class salvarrelatorio(APIView):
    # Desativa a autenticacao padrao do DRF que forca o CSRF mesmo com o @csrf_exempt
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            # Recupera o ID e e-mail do usuario salvo na sessao do Django
            ideusuario = request.session.get('ideusuario')
            desemail = request.session.get('desemail')

            if not ideusuario:
                return Response({'erro': 'Sessao expirada ou usuario nao autenticado.'}, status=status.HTTP_401_UNAUTHORIZED)

            desnomediagnostico = request.data.get('desnomediagnostico')
            descrelatorio = request.data.get('descrelatorio')

            if not desnomediagnostico or not descrelatorio:
                return Response({'erro': 'Campos obrigatorios ausentes.'}, status=status.HTTP_400_BAD_REQUEST)

            # Instancia a conexao atraves da sua classe personalizada
            banco = conn().banco
            cursor = banco.cursor()

            # Executa a Stored Procedure
            cursor.callproc('spinsrelatorio', [
                ideusuario,
                desnomediagnostico,
                descrelatorio
            ])

            row = cursor.fetchone()
            iderelatorio = row[0] if row else None

            # Finaliza a transacao e fecha a conexao
            banco.commit()
            cursor.close()
            banco.close()

            # Envio do e-mail via biblioteca oficial do Resend
            if desemail:
                try:
                    resend.Emails.send({
                       "from": "onboarding@resend.dev",
                        "to": desemail,
                        "subject": f"RelatÃ³rio Salvo: {desnomediagnostico}",
                        "html": f"<p>OlÃ¡,</p><p>Seu relatÃ³rio <strong>{desnomediagnostico}</strong> foi salvo com sucesso!</p><p><strong>Resumo:</strong> {descrelatorio}</p>"
                    })
                except Exception as erro_email:
                    print(f"Falha ao enviar e-mail: {erro_email}")

            return Response({
                'sucesso': True,
                'mensagem': 'Relatorio salvo com sucesso.',
                'iderelatorio': iderelatorio
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            if 'banco' in locals() and banco:
                banco.rollback()
                cursor.close()
                banco.close()
            return Response({'erro': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class listarrelatoriosusuario(APIView):
    def get(self, request):
        try:
            ideusuariovar = request.session.get('ideusuario')
            if not ideusuariovar:
                return Response({'erro': 'Sessao expirada ou usuario nao autenticado.'}, status=status.HTTP_401_UNAUTHORIZED)

            conexaobanco = conn().banco
            cursorbanco = conexaobanco.cursor()
            cursorbanco.callproc('spselrelatorioporusuario', [ideusuariovar])
            rowsbanco = cursorbanco.fetchall()
            cursorbanco.close()
            conexaobanco.close()

            relatorioslist = []
            for rowbanco in rowsbanco:
                relatorioslist.append({
                    'iderelatorio': rowbanco[0],
                    'desnomediagnostico': rowbanco[1],
                    'descrelatorio': rowbanco[2],
                    'dtcregistro': str(rowbanco[3]) if rowbanco[3] else '',
                    'stsativo': rowbanco[4],
                    'stsdeletado': rowbanco[5]
                })

            return Response(relatorioslist, status=status.HTTP_200_OK)

        except Exception as erroexcecao:
            if 'conexaobanco' in locals() and conexaobanco:
                conexaobanco.rollback()
                cursorbanco.close()
                conexaobanco.close()
            return Response({'erro': str(erroexcecao)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class obterrelatorioporid(APIView):
    def get(self, request, iderelatorio):
        try:
            conexaobanco = conn().banco
            cursorbanco = conexaobanco.cursor()
            cursorbanco.callproc('spselrelatorioporide', [iderelatorio])
            rowbanco = cursorbanco.fetchone()
            cursorbanco.close()
            conexaobanco.close()

            if not rowbanco:
                return Response({'erro': 'Relatorio nao encontrado.'}, status=status.HTTP_404_NOT_FOUND)

            relatoriotic = {
                'ideusuario': rowbanco[0],
                'desnomediagnostico': rowbanco[1],
                'descrelatorio': rowbanco[2],
                'dtcregistro': str(rowbanco[3]) if rowbanco[3] else '',
                'stsativo': rowbanco[4],
                'stsdeletado': rowbanco[5],
                'desnomeusuario': rowbanco[6]
            }

            return Response(relatoriotic, status=status.HTTP_200_OK)

        except Exception as erroexcecao:
            if 'conexaobanco' in locals() and conexaobanco:
                conexaobanco.rollback()
                cursorbanco.close()
                conexaobanco.close()
            return Response({'erro': str(erroexcecao)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class enviarpdfporemail(APIView):
    def post(self, request, iderelatorio):
        try:
            desemailvar = request.session.get('desemail')
            if not desemailvar:
                return Response({'erro': 'Sessao expirada ou usuario nao autenticado.'}, status=status.HTTP_401_UNAUTHORIZED)

            conexaobanco = conn().banco
            cursorbanco = conexaobanco.cursor()
            cursorbanco.callproc('spselrelatorioporide', [iderelatorio])
            rowbanco = cursorbanco.fetchone()
            cursorbanco.close()
            conexaobanco.close()

            if not rowbanco:
                return Response({'erro': 'Relatorio nao encontrado.'}, status=status.HTTP_404_NOT_FOUND)

            desnomediagnosticostr = rowbanco[1]
            descrelatoriostr = rowbanco[2]
            dtcregistrostr = str(rowbanco[3]) if rowbanco[3] else ''

            # ----------------------------------------------------
            # GeraÃ§Ã£o do PDF em MemÃ³ria (Buffer)
            # ----------------------------------------------------
            bufferpdf = io.BytesIO()
            pdivcanvas = canvas.Canvas(bufferpdf, pagesize=letter)
            
            # CabeÃ§alho no PDF
            pdivcanvas.setFont("Helvetica-Bold", 16)
            pdivcanvas.drawString(50, 750, "SGRUB - Sistema de Gestao de Residuos")
            pdivcanvas.line(50, 740, 560, 740)

            # ConteÃºdo do RelatÃ³rio
            pdivcanvas.setFont("Helvetica-Bold", 12)
            pdivcanvas.drawString(50, 700, f"Relatorio ID: {iderelatorio}")
            pdivcanvas.drawString(50, 680, f"Diagnostico: {desnomediagnosticostr}")
            pdivcanvas.drawString(50, 660, f"Data de Registro: {dtcregistrostr}")

            pdivcanvas.setFont("Helvetica-Bold", 12)
            pdivcanvas.drawString(50, 620, "Descricao Completa:")
            
            pdivcanvas.setFont("Helvetica", 10)
            textobject = pdivcanvas.beginText(50, 600)
            textobject.textLines(descrelatoriostr)
            pdivcanvas.drawText(textobject)

            pdivcanvas.showPage()
            pdivcanvas.save()
            
            pdfbytes = bufferpdf.getvalue()
            bufferpdf.close()

            # ----------------------------------------------------
            # Envio do E-mail com Anexo PDF via Resend
            # ----------------------------------------------------
            resend.Emails.send({
                "from": "onboarding@resend.dev",
                "to": desemailvar,
                "subject": f"RelatÃ³rio PDF - {desnomediagnosticostr}",
                "html": "<p>OlÃ¡,</p><p>Segue em anexo o relatÃ³rio completo em formato PDF gerado pelo sistema SGRUB.</p>",
                "attachments": [
                    {
                        "filename": f"relatorio_{iderelatorio}.pdf",
                        "content": list(pdfbytes)
                    }
                ]
            })

            return Response({'sucesso': True, 'mensagem': 'PDF enviado por e-mail com sucesso!'}, status=status.HTTP_200_OK)

        except Exception as erroexcecao:
            return Response({'erro': str(erroexcecao)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class deletarrelatorio(APIView):
    def post(self, request, iderelatorio):
        try:
            # Recupera o ID do usuÃ¡rio logado na sessÃ£o do Django
            ideusuariologado = request.session.get('ideusuario')
            if not ideusuariologado:
                return Response({'erro': 'Sessao expirada ou usuario nao autenticado.'}, status=status.HTTP_401_UNAUTHORIZED)

            banco = conn().banco
            cursor = banco.cursor()

            # Executa a Stored Procedure de exclusÃ£o lÃ³gica que vocÃª criou
            cursor.callproc('spupddeletarrelatorio', [
                iderelatorio,
                ideusuariologado
            ])

            # Finaliza a transaÃ§Ã£o e fecha a conexÃ£o
            banco.commit()
            cursor.close()
            banco.close()

            return Response({
                'sucesso': True,
                'mensagem': 'RelatÃ³rio excluÃ­do com sucesso.'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            if 'banco' in locals() and banco:
                banco.rollback()
                cursor.close()
                banco.close()
            return Response({'erro': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

