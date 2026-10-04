"""Testes do pacote de precisão v4.11.0: validação de chamadas, termômetro
de risco e intents offline."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import intents, precisao

DECLS = [
    {"name": "clima", "description": "clima",
     "parameters": {"type": "object",
                    "properties": {"cidade": {"type": "string"}},
                    "required": []}},
    {"name": "abrir_site", "description": "abre site",
     "parameters": {"type": "object",
                    "properties": {"url": {"type": "string", "description": "URL"}},
                    "required": ["url"]}},
    {"name": "controlar_volume", "description": "volume",
     "parameters": {"type": "object",
                    "properties": {"acao": {"type": "string",
                                            "enum": ["aumentar", "diminuir",
                                                     "silenciar", "maximo"]}},
                    "required": []}},
    {"name": "definir_timer", "description": "timer",
     "parameters": {"type": "object",
                    "properties": {"segundos": {"type": "number"},
                                    "motivo": {"type": "string"}},
                    "required": ["segundos"]}},
]


class TestaValidacao(unittest.TestCase):
    def test_tool_desconhecida(self):
        err = precisao.valida_chamada("nao_existe", {}, DECLS)
        self.assertIsNotNone(err)
        self.assertIn("não existe", err)

    def test_obrigatorio_faltando(self):
        err = precisao.valida_chamada("abrir_site", {}, DECLS)
        self.assertIsNotNone(err)
        self.assertIn("url", err)

    def test_obrigatorio_vazio(self):
        err = precisao.valida_chamada("abrir_site", {"url": "  "}, DECLS)
        self.assertIsNotNone(err)

    def test_tipo_errado(self):
        err = precisao.valida_chamada("definir_timer", {"segundos": "dez"}, DECLS)
        self.assertIsNotNone(err)
        self.assertIn("number", err)

    def test_fora_do_enum(self):
        err = precisao.valida_chamada("controlar_volume", {"acao": "explode"}, DECLS)
        self.assertIsNotNone(err)
        self.assertIn("aumentar", err)

    def test_chamada_valida(self):
        self.assertIsNone(precisao.valida_chamada("clima", {"cidade": "Recife"}, DECLS))
        self.assertIsNone(precisao.valida_chamada("clima", {}, DECLS))
        self.assertIsNone(precisao.valida_chamada("definir_timer",
                                                 {"segundos": 60, "extra": "ok"}, DECLS))
        self.assertIsNone(precisao.valida_chamada("controlar_volume",
                                                 {"acao": "maximo"}, DECLS))


class TestaRisco(unittest.TestCase):
    def test_apagar_arquivo_pedem_confirmacao(self):
        self.assertIsNotNone(precisao.avalia_risco(
            "file_controller", {"operation": "delete_file", "path": "x.txt"}))
        self.assertIsNotNone(precisao.avalia_risco(
            "file_controller", {"operation": "move_file"}))
        self.assertIsNotNone(precisao.avalia_risco(
            "send_message", {"contact": "Ana", "message": "oi"}))
        self.assertIsNotNone(precisao.avalia_risco(
            "computer_control", {"action": "click"}))

    def test_acoes_inofensivas_livres(self):
        self.assertIsNone(precisao.avalia_risco("clima", {"cidade": "Recife"}))
        self.assertIsNone(precisao.avalia_risco("abrir_app", {"app": "calc"}))
        self.assertIsNone(precisao.avalia_risco(
            "file_controller", {"operation": "list_files"}))
        self.assertIsNone(precisao.avalia_risco(
            "desktop", {"operation": "list_icons"}))


class TestaIntents(unittest.TestCase):
    def exec_falso(self):
        chamadas = []
        def executa(name, args):
            chamadas.append((name, args))
            return f"OK {name}"
        return executa, chamadas

    def test_hora(self):
        r = intents.reconhecer("que horas são?", self.exec_falso()[0])
        self.assertIsNotNone(r)
        self.assertIn("senhor", r[0])
        self.assertIn(":", r[0])

    def test_data(self):
        r = intents.reconhecer("que dia é hoje", self.exec_falso()[0])
        self.assertIsNotNone(r)
        self.assertTrue(any(d in r[0] for d in intents.DIAS))

    def test_status(self):
        exe, _ = self.exec_falso()
        r = intents.reconhecer("status do pc", exe)
        self.assertIsNotNone(r)

    def test_abrir_app(self):
        exe, chamadas = self.exec_falso()
        r = intents.reconhecer("abre o bloco de notas", exe)
        self.assertIsNotNone(r)
        self.assertEqual(chamadas[0][0], "abrir_app")
        self.assertEqual(chamadas[0][1]["app"], "bloco de notas")

    def test_volume_e_musica(self):
        exe, chamadas = self.exec_falso()
        self.assertIsNotNone(intents.reconhecer("aumenta o volume", exe))
        self.assertEqual(chamadas[-1], ("controlar_volume", {"acao": "aumentar"}))
        self.assertIsNotNone(intents.reconhecer("toca música de rock", exe))
        self.assertEqual(chamadas[-1][0], "tocar_musica")

    def test_timer(self):
        exe, chamadas = self.exec_falso()
        r = intents.reconhecer("me avisa em 10 minutos pra tirar o pão", exe)
        self.assertIsNotNone(r)
        self.assertEqual(chamadas[0][0], "definir_timer")
        self.assertEqual(chamadas[0][1]["segundos"], 600)

    def test_conversa_normal_nao_e_sequestrada(self):
        exe, _ = self.exec_falso()
        # frases de conversa e pedidos complexos seguem pro cérebro
        self.assertIsNone(intents.reconhecer("abre o link da compra que mandei ontem, senhor", exe))
        self.assertIsNone(intents.reconhecer(
            "que horas o ônibus passa aqui perto de casa", exe))
        self.assertIsNone(intents.reconhecer(
            "me escreve um email pro chefe falando do relatório", exe))
        self.assertIsNone(intents.reconhecer("", exe))
        self.assertIsNone(intents.reconhecer("a" * 200, exe))


if __name__ == "__main__":
    unittest.main()
