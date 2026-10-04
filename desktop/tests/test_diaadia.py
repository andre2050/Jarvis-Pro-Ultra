"""Testes do Kit do Dia a Dia (v4.13.0): briefing, busca de arquivos,
controle de mídia e calculadora offline."""
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import agenda, briefing, intents, tools


class ComArquivoTemp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        agenda.AGENDA_FILE = self.tmp / "agenda.json"
        briefing.ESTADO_FILE = self.tmp / "briefing.json"


class TestaBriefing(ComArquivoTemp):
    def test_gera_com_saudacao_e_data(self):
        msg = briefing.gerar()
        agora = datetime.now()
        self.assertTrue(any(d in msg for d in briefing.DIAS), msg)
        self.assertIn(agora.strftime("%d/%m/%Y"), msg)
        self.assertIn("senhor", msg)
        self.assertIn("agenda", msg)

    def test_agenda_do_dia_entra_no_briefing(self):
        agenda.agendar("amanhã 07:30", "acordar cedo")
        msg = briefing.gerar()
        # 'amanhã' pode cair no dia seguinte: garante que não quebra
        self.assertIsInstance(msg, str)
        agenda.agendar("23:59", "fechar a loja")
        msg = briefing.gerar()
        if datetime.now().strftime("%H:%M") != "23:59":
            self.assertIn("fechar a loja", msg)

    def test_uma_vez_por_dia(self):
        hoje = datetime.now()
        if hoje.hour < 5:
            self.skipTest("antes das 5h o briefing não dispara")
        primeiro = briefing.do_boot()
        self.assertIsNotNone(primeiro)
        segundo = briefing.do_boot()
        self.assertIsNone(segundo)


class TestaProcuraArquivos(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "relatorio vendas.xlsx").write_text("x")
        (self.tmp / "RELATORIO_old.xlsx").write_text("x")
        (self.tmp / "outra_coisa.txt").write_text("x")
        real = tools._pastas_usuario

        def fake():
            return {"documentos": self.tmp}
        tools._pastas_usuario = fake
        self._real = real

    def tearDown(self):
        tools._pastas_usuario = self._real

    def test_acha_sem_acento_e_sem_caixa(self):
        r = tools._procurar_arquivos("Relatório", "documentos")
        self.assertIn("relatorio vendas.xlsx", r)
        self.assertIn("RELATORIO_old.xlsx", r)
        self.assertNotIn("outra_coisa.txt", r)

    def test_nao_achou_avisa_honesto(self):
        r = tools._procurar_arquivos("zzz_inexistente_zzz", "documentos")
        self.assertIn("Nenhum arquivo", r)

    def test_executa_pela_rota_oficial(self):
        r = tools.execute("procurar_arquivos",
                          {"nome": "relatorio vendas", "pasta": "documentos"})
        self.assertIn("relatorio vendas.xlsx", r)


class TestaMidia(unittest.TestCase):
    def test_executa_sem_crash_fora_do_windows(self):
        r = tools.execute("controlar_midia", {"acao": "play_pause"})
        self.assertIsInstance(r, str)
        self.assertIn("senhor", r)

    def test_acao_invalida(self):
        r = tools.execute("controlar_midia", {"acao": "explode"})
        self.assertIn("inválida", r)


class TestaCalculadora(unittest.TestCase):
    def calc(self, frase):
        r = intents.reconhecer(frase, lambda n, a: "TOOL")
        return r[0] if r else None

    def test_operacoes(self):
        self.assertIn("75", self.calc("quanto é 25*3"))
        self.assertIn("14", self.calc("calcula 2+3*4"))  # precedência: 3*4 antes do 2+

    def test_por_extenso(self):
        self.assertIn("4", self.calc("quanto é 2 mais 2"))
        self.assertIn("10", self.calc("quanto é 5 vezes 2"))

    def test_virgula_decimal(self):
        self.assertIn("3.5", self.calc("quanto é 2,5+1"))

    def test_pergunta_nao_matematica_segue_pro_cerebro(self):
        self.assertIsNone(self.calc("quanto é o boleto da vivo"))
        self.assertIsNone(self.calc("quanto é isso real pra você"))
        self.assertIsNone(self.calc("calcula minha sorte"))

    def test_bomba_de_potencia_recusada(self):
        self.assertIsNone(self.calc("quanto é 99999999999999999999999999999**999999"))


class TestaIntentsMidia(unittest.TestCase):
    def test_pausa_e_pula(self):
        chamadas = []

        def executa(name, args):
            chamadas.append((name, args))
            return "OK"
        self.assertIsNotNone(intents.reconhecer("pausa a música", executa))
        self.assertEqual(chamadas[-1], ("controlar_midia", {"acao": "play_pause"}))
        self.assertIsNotNone(intents.reconhecer("próxima música", executa))
        self.assertEqual(chamadas[-1], ("controlar_midia", {"acao": "proxima"}))
        self.assertIsNotNone(intents.reconhecer("volta a música", executa))
        self.assertEqual(chamadas[-1], ("controlar_midia", {"acao": "anterior"}))

    def test_frase_completa_nao_e_sequestrada(self):
        # "toca música de rock" continua indo pra tocar_musica, não pro play/pause
        chamadas = []

        def executa(name, args):
            chamadas.append((name, args))
            return "OK"
        intents.reconhecer("toca música de rock", executa)
        self.assertEqual(chamadas[0][0], "tocar_musica")


if __name__ == "__main__":
    unittest.main()
