"""Testes do agendador persistente, da busca por relevância (v4.12.0) e do
intent de aviso com hora marcada."""
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import agenda, intents, memory


class ComArquivoTemp(unittest.TestCase):
    """Aponta agenda.json e memory.json pra um diretório temporário."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        agenda.AGENDA_FILE = self.tmp / "agenda.json"
        memory.MEMORY_FILE = self.tmp / "memory.json"


class TestaAgenda(ComArquivoTemp):
    def test_parse_horarios(self):
        agora = datetime.now()
        h = agenda._parse_horario("18:30")
        self.assertIsNotNone(h)
        self.assertGreaterEqual(h, agora)
        h = agenda._parse_horario("amanhã 08:00")
        self.assertEqual(h.hour, 8)
        self.assertEqual((h.date() - agora.date()).days, 1)
        self.assertIsNotNone(agenda._parse_horario("05/12 09:00"))
        self.assertIsNotNone(agenda._parse_horario("05/12/2026 09:00"))
        self.assertIsNotNone(agenda._parse_horario("2026-12-05T09:00"))
        self.assertIsNone(agenda._parse_horario("quando eu lembra"))

    def test_agendar_lista_cancelar(self):
        r = agenda.agendar("23:59", "pagar o boleto da Vivo")
        self.assertIn("Agendado", r)
        r = agenda.agendar("amanhã 07:30", "acordar cedo")
        self.assertIn("Agendado", r)
        lista = agenda.listar()
        self.assertIn("pagar o boleto", lista)
        self.assertIn("#1", lista) and self.assertIn("#2", lista)
        r = agenda.cancelar(1)
        self.assertIn("Cancelado", r)
        self.assertNotIn("pagar o boleto", agenda.listar())
        self.assertIn("não encontrei", agenda.cancelar(99))

    def test_horario_invalido_devolve_erro_pro_modelo(self):
        r = agenda.agendar("quinta que vem", "jogo")
        self.assertIn("[ARGUMENTOS INVÁLIDOS]", r)
        r = agenda.agendar("18:30", "")
        self.assertIn("[ARGUMENTOS INVÁLIDOS]", r)

    def test_devidos_dispara_e_remove(self):
        agenda.agendar("18:30", "aviso 1")
        # vence um aviso no passado: acontece se o app estava fechado
        data = agenda._load()
        data["avisos"][0]["quando"] = (datetime.now() - timedelta(hours=2)).isoformat(timespec="minutes")
        agenda._save(data)
        prontos = agenda.devidos()
        self.assertEqual(len(prontos), 1)
        self.assertEqual(prontos[0][0], "aviso 1")
        # segunda passada: já foi consumido
        self.assertEqual(agenda.devidos(), [])

    def test_persistencia_entre_reloads(self):
        agenda.agendar("amanhã 06:00", "lembrete persistente")
        # simula fechar e abrir o app: o arquivo é a fonte da verdade
        prontos = agenda.devidos()
        self.assertEqual(prontos, [])
        lista = agenda.listar()
        self.assertIn("lembrete persistente", lista)


class TestaMemoriaRanqueada(ComArquivoTemp):
    def test_ranking_por_relevancia(self):
        memory.lembrar("Meu jogo favorito é futebol de botão")
        memory.lembrar("O boleto da Vivo vence todo dia 5")
        memory.lembrar("Prefiro suco de maracujá sem açúcar")
        r = memory.buscar("quando vence o boleto da vivo")
        self.assertTrue(any("boleto" in x for x in r), r)
        self.assertTrue(any("Vivo" in x for x in r), r)
        self.assertFalse(any("futebol" in x for x in r), r)
        self.assertFalse(any("maracujá" in x for x in r), r)

    def test_acento_e_caixa_nao_enganam(self):
        memory.lembrar("Vacinação do cachorro todo ano em fevereiro")
        r = memory.buscar("me lembra da VACINACAO")
        self.assertTrue(any("Vacinação" in x for x in r), r)

    def test_stopword_nao_puxa_tudo(self):
        memory.lembrar("O André gosta de praia")
        memory.lembrar("Nada guardado relevante")
        r = memory.buscar("como que que")
        self.assertEqual(r, [])


class TestaIntentAgenda(unittest.TestCase):
    def test_aviso_com_hora_marcada(self):
        chamadas = []

        def executa(name, args):
            chamadas.append((name, args))
            return "OK"

        r = intents.reconhecer("às 18:30 me avisa do boleto da Vivo", executa)
        self.assertIsNotNone(r)
        self.assertEqual(chamadas[0][0], "agendar_aviso")
        self.assertEqual(chamadas[0][1]["horario"], "18:30")
        self.assertIn("boleto da Vivo", chamadas[0][1]["motivo"])

    def test_amanha_e_complemento(self):
        chamadas = []

        def executa(name, args):
            chamadas.append((name, args))
            return "OK"

        r = intents.reconhecer("amanhã às 8h me lembra de acordar cedo", executa)
        self.assertIsNotNone(r)
        self.assertEqual(chamadas[0][1]["horario"], "amanhã 08:00")
        self.assertIn("acordar cedo", chamadas[0][1]["motivo"])

    def test_contagem_segue_pro_timer(self):
        chamadas = []

        def executa(name, args):
            chamadas.append((name, args))
            return "OK"

        intents.reconhecer("me avisa em 10 minutos pra tirar o pão", executa)
        self.assertEqual(chamadas[0][0], "definir_timer")


if __name__ == "__main__":
    unittest.main()
