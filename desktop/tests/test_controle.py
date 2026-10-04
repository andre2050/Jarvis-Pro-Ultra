"""Testes da Central de Controle (v4.14.0): backup, diagnóstico, trato,
editor de memórias, tools do PC, busca resumida e modo econômico."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import backup, diagnostico, memory, precisao, tools


class ComArquivoTemp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        backup.CONFIG_DIR = self.tmp
        memory.MEMORY_FILE = self.tmp / "memory.json"
        tools._cfg = {}


class TestaBackup(ComArquivoTemp):
    def test_exporta_e_importa(self):
        memory.lembrar("lembrar do aniversário da mãe")
        zip_path = self.tmp / "backup.zip"
        r = backup.exportar(str(zip_path))
        self.assertIn("Backup criado", r)
        self.assertTrue(zip_path.exists())
        # apaga tudo e restaura
        memory.limpar()
        self.assertIn("Nenhuma", memory.listar())
        r = backup.importar(str(zip_path))
        self.assertIn("restaurado", r)
        self.assertIn("aniversário", memory.listar())

    def test_zip_errado_recusado(self):
        (self.tmp / "falso.zip").write_text("não sou um zip")
        r = backup.importar(str(self.tmp / "falso.zip"))
        self.assertIn("corrompido", r)
        r = backup.importar("/caminho/que/não/existe.zip")
        self.assertIn("não achei", r)


class TestaDiagnostico(unittest.TestCase):
    def test_roda_e_cobre_as_famillias(self):
        resultados = diagnostico.rodar()
        nomes = [n for n, _, _ in resultados]
        self.assertIn("hora_agora", nomes)
        self.assertIn("ver_tela (visão)", nomes)
        self.assertIn("ditado por voz (Whisper)", nomes)
        # as tools executadas de verdade responderam
        for nome, ok, _ in resultados:
            if nome == "hora_agora":
                self.assertTrue(ok)


class TestaTratoPersonalizado(unittest.TestCase):
    def test_prompt_formal_e_descontraido(self):
        from core import brain
        p = brain.system_prompt({"nome_usuario": "André Menezes",
                                 "estilo": "formal"})
        self.assertIn("'senhor'", p)
        p = brain.system_prompt({"nome_usuario": "André Menezes",
                                 "estilo": "descontraido"})
        self.assertIn("'André'", p)
        self.assertNotIn("Chame o usuário de 'senhor'", p)
        p = brain.system_prompt({"nome_assistente": "ORION"})
        self.assertIn("ORION", p)


class TestaEditorMemorias(ComArquivoTemp):
    def test_atualizar_mantem_data(self):
        memory.lembrar("odeio segunda-feira")
        data = memory.dados()[0]["data"]
        r = memory.atualizar("odeio segunda-feira", "odeio segunda e terça")
        self.assertIn("atualizada", r)
        m = memory.dados()[0]
        self.assertEqual(m["texto"], "odeio segunda e terça")
        self.assertEqual(m["data"], data)
        self.assertIn("não encontrei", memory.atualizar("nunca existiu", "x"))


class TestaComandosPC(ComArquivoTemp):
    def test_info_disco_responde(self):
        r = tools.execute("info_disco", {})
        self.assertIn("GB", r)
        self.assertIn("senhor", r)

    def test_bloquear_tela_nao_crasha(self):
        r = tools.execute("bloquear_tela", {})
        self.assertIsInstance(r, str)

    def test_lixeira_ped_confirmacao(self):
        self.assertIsNotNone(precisao.avalia_risco("limpar_lixeira", {}))
        # fora do Windows avisa em vez de fingir
        import sys
        if not sys.platform.startswith("win"):
            self.assertIn("só funciona no Windows",
                          tools.execute("limpar_lixeira", {}))

    def test_ler_voz_alta(self):
        falado = []
        tools.on_falar = lambda t: falado.append(t)
        r = tools.execute("ler_em_voz_alta", {"texto": "bom dia, senhor"})
        self.assertIn("lendo", r)
        self.assertEqual(falado, ["bom dia, senhor"])
        r = tools.execute("ler_em_voz_alta", {"texto": ""})
        self.assertIn("nada pra ler", r)
        tools.on_falar = lambda t: None


class TestaBuscaResumida(ComArquivoTemp):
    def test_sem_busca_avisa(self):
        r = tools.execute("pesquisar_resumido", {"busca": ""})
        self.assertIn("diga o que pesquisar", r)

    def test_sem_chave_devolve_topicos_honestos(self):
        # monkeypatch na DDGS pra não depender de rede no teste
        import types
        fake = types.ModuleType("ddgs")

        class _DDGS:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def text(self, q, **kw):
                return [{"title": "Resultado 1", "body": "trecho do resultado",
                         "href": "https://exemplo.com/1"}]

        fake.DDGS = _DDGS
        sys.modules["ddgs"] = fake
        try:
            r = tools.execute("pesquisar_resumido", {"busca": "qualquer coisa"})
            self.assertIn("exemplo.com", r)
            self.assertIn("Resultado 1", r)
        finally:
            del sys.modules["ddgs"]


class TestaModoEconomico(unittest.TestCase):
    def test_reactor_aceita_economia(self):
        # o intervalo do loop muda com o atributo; aqui só garantimos a API
        from ui.reactor import ArcReactorHud
        self.assertTrue(hasattr(ArcReactorHud, "_frame"))


if __name__ == "__main__":
    unittest.main()
